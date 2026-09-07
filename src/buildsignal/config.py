"""Strict TOML configuration and local endpoint validation."""

import ipaddress
import re
import tomllib
from pathlib import Path
from urllib.parse import urlsplit


class BuildSignalError(Exception):
    """An expected, actionable failure."""


DEFAULT = {
    "scan": {
        "days": 45,
        "max_issues": 100,
        "max_releases": 20,
        "max_opportunities": 8,
        "threshold": 0.28,
        "minimum_score": 25.0,
    },
    "enrichment": {
        "enabled": False,
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "",
        "allow_remote": False,
        "api_key_env": "",
    },
}


def validate_endpoint(url, allow_remote=False):
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (ValueError, TypeError) as exc:
        raise BuildSignalError("Invalid model endpoint") from exc
    del port
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise BuildSignalError("Model endpoint must be HTTP(S), without credentials/query/fragment")
    try:
        loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        # Use numeric loopback addresses to avoid DNS changing the destination.
        loopback = False
    if not loopback and not allow_remote:
        raise BuildSignalError("Use numeric loopback (127.0.0.1 or ::1), or set allow_remote=true")
    if not loopback and parsed.scheme != "https":
        raise BuildSignalError("Remote enrichment requires HTTPS")


def load_config(path):
    try:
        with Path(path).open("rb") as stream:
            raw = tomllib.load(stream)
    except (OSError, ValueError) as exc:
        raise BuildSignalError(f"Cannot read configuration: {exc}") from exc
    if set(raw) - {"scan", "enrichment", "repositories"}:
        raise BuildSignalError("Unknown top-level configuration key")
    config = {}
    for section, defaults in DEFAULT.items():
        values = raw.get(section, {})
        if not isinstance(values, dict) or set(values) - set(defaults):
            raise BuildSignalError(f"Unknown key or invalid [{section}] section")
        config[section] = defaults | values
        for key, default in defaults.items():
            value = config[section][key]
            if type(default) is float:
                valid = type(value) in (int, float)
            else:
                valid = type(value) is type(default)
            if not valid:
                raise BuildSignalError(f"Invalid type for {section}.{key}")
    limits = {
        "days": (1, 365),
        "max_issues": (1, 500),
        "max_releases": (1, 100),
        "max_opportunities": (1, 50),
        "threshold": (0.05, 0.95),
        "minimum_score": (0, 100),
    }
    for key, (low, high) in limits.items():
        if not low <= config["scan"][key] <= high:
            raise BuildSignalError(f"scan.{key} must be between {low} and {high}")
    repos = raw.get("repositories", [])
    if not isinstance(repos, list) or not 1 <= len(repos) <= 30:
        raise BuildSignalError("Configure 1 to 30 [[repositories]]")
    names = []
    for repo in repos:
        if not isinstance(repo, dict) or set(repo) != {"name"}:
            raise BuildSignalError("Each repository must contain only name")
        name = repo["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", name, re.ASCII):
            raise BuildSignalError("Repository name must be owner/name")
        if any(part in {".", ".."} for part in name.split("/")):
            raise BuildSignalError("Invalid repository name")
        names.append(name)
    if len({name.lower() for name in names}) != len(names):
        raise BuildSignalError("Duplicate repositories")
    config["repositories"] = names
    enrich = config["enrichment"]
    validate_endpoint(enrich["base_url"], enrich["allow_remote"])
    return config
