"""Bounded read-only GitHub REST client with ETag caching."""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .config import BuildSignalError

MAX_BYTES = 8 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(url, *, headers=None, data=None, local=False):
    handlers = [NoRedirect()]
    if local:
        handlers.append(ProxyHandler({}))
    request = Request(url, headers=headers or {}, data=data)
    try:
        with build_opener(*handlers).open(request, timeout=30) as response:
            payload = response.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise BuildSignalError("Response exceeds 8 MiB limit")
            return response.status, dict(response.headers.items()), json.loads(payload)
    except HTTPError as exc:
        if exc.code == 304:
            return 304, {}, None
        raise BuildSignalError(
            f"HTTP {exc.code}; check access/rate limits. No redirects are followed."
        ) from None
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        # Do not include headers, URL credentials, or remote bodies in error output.
        raise BuildSignalError(f"Request failed ({type(exc).__name__})") from None


class Cache:
    def __init__(self, directory, ttl=21600):
        self.directory = Path(directory)
        self.ttl = ttl

    def path(self, key):
        return self.directory / (hashlib.sha256(key.encode()).hexdigest() + ".json")

    def get(self, key):
        try:
            entry = json.loads(self.path(key).read_text())
            if not isinstance(entry, dict) or not {"data", "time", "etag"} <= entry.keys():
                return None
            if not isinstance(entry["time"], (int, float)):
                return None
            return entry
        except (OSError, ValueError, TypeError):
            return None

    def put(self, key, data, etag=""):
        self.directory.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.directory, delete=False) as f:
                name = f.name
                json.dump({"data": data, "etag": etag, "time": time.time()}, f)
            os.replace(name, self.path(key))
        finally:
            if name and os.path.exists(name):
                os.unlink(name)


class GitHub:
    def __init__(self, cache, token=None, transport=request_json):
        self.cache = cache
        self.token = os.environ.get("GITHUB_TOKEN", "") if token is None else token
        self.transport = transport
        self.last_search = 0.0

    def get(self, path, params=None, cacheable=True):
        url = "https://api.github.com" + path
        if params:
            url += "?" + urlencode(params)
        entry = self.cache.get(url) if cacheable else None
        if entry and 0 <= time.time() - entry["time"] < self.cache.ttl:
            return entry["data"]
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "buildsignal-ai/0.1",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if entry and entry["etag"]:
            headers["If-None-Match"] = entry["etag"]
        if path == "/search/repositories":
            # Unauthenticated search has a separate low request budget.
            delay = (2.1 if self.token else 6.1) - (time.monotonic() - self.last_search)
            if delay > 0:
                time.sleep(delay)
            self.last_search = time.monotonic()
        status, response_headers, data = self.transport(url, headers=headers)
        if status == 304 and entry:
            data = entry["data"]
        elif status != 200:
            raise BuildSignalError(f"Unexpected HTTP status {status}")
        if cacheable:
            normalized = {k.lower(): v for k, v in response_headers.items()}
            self.cache.put(url, data, normalized.get("etag", entry["etag"] if entry else ""))
        return data

    def public_repository(self, name):
        # Never reuse cached visibility: a public repository may become private.
        result = self.get(f"/repos/{name}", cacheable=False)
        if not isinstance(result, dict) or result.get("private") is not False:
            raise BuildSignalError(f"Refusing non-public or unverified repository: {name}")

    def items(self, name, kind, limit, since=None):
        items = []
        for page in range(1, (limit + 99) // 100 + 1):
            params = {"per_page": min(limit, 100), "page": page}
            if kind == "issues":
                params.update(state="open", sort="updated", direction="desc", since=since)
            data = self.get(f"/repos/{name}/{kind}", params)
            if not isinstance(data, list):
                raise BuildSignalError(f"Invalid {kind} response")
            items.extend(data)
            if len(data) < params["per_page"]:
                break
        return items[:limit]

    def competition(self, keywords):
        query = " ".join(keywords[:3]) + " in:name,description,readme archived:false"
        result = self.get("/search/repositories", {"q": query, "per_page": 5})
        if not isinstance(result, dict) or result.get("incomplete_results"):
            raise BuildSignalError("Competition search incomplete")
        return {
            "query": query,
            "total_count": result.get("total_count", 0),
            "repositories": [
                {"name": r["full_name"], "url": r["html_url"]}
                for r in result.get("items", [])
                if not r.get("private", True)
            ],
        }
