import copy
import json
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from buildsignal.analysis import cluster, collect, date, normalize, rank, score, tokens, WEIGHTS
from buildsignal.cli import FixtureClient, main, run
from buildsignal.config import BuildSignalError, DEFAULT, load_config, validate_endpoint
from buildsignal.github import Cache, GitHub, NoRedirect
from buildsignal.report import enrich, escape, safe_url

NOW = date("2026-09-07T00:00:00Z")


class BuildSignalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.config = load_config(files("buildsignal").joinpath("demo.toml"))
        self.client = FixtureClient(files("buildsignal").joinpath("demo.json"))
        self.signals = collect(self.client, self.config, NOW)

    def config_file(self, text):
        path = self.directory / "config.toml"
        path.write_text(text)
        return path

    def opportunity(self):
        return rank(cluster(self.signals), self.client, self.config, NOW)[0][0]

    def test_default_config(self):
        config = load_config(files("buildsignal").joinpath("default.toml"))
        self.assertEqual(len(config["repositories"]), 6)

    def test_unknown_config_key(self):
        with self.assertRaises(BuildSignalError):
            load_config(self.config_file("surprise = true"))

    def test_duplicate_repositories(self):
        with self.assertRaises(BuildSignalError):
            load_config(
                self.config_file('[[repositories]]\nname="a/b"\n[[repositories]]\nname="A/B"')
            )

    def test_strict_numeric_types(self):
        with self.assertRaises(BuildSignalError):
            load_config(self.config_file('[scan]\ndays=true\n[[repositories]]\nname="a/b"'))

    def test_nan_rejected(self):
        with self.assertRaises(BuildSignalError):
            load_config(self.config_file('[scan]\nthreshold=nan\n[[repositories]]\nname="a/b"'))

    def test_remote_endpoint_needs_opt_in(self):
        with self.assertRaises(BuildSignalError):
            validate_endpoint("https://example.com/v1")
        validate_endpoint("https://example.com/v1", True)

    def test_remote_http_and_url_credentials_rejected(self):
        for url in ("http://example.com", "https://user:password@example.com", "file:///tmp/a"):
            with self.subTest(url=url), self.assertRaises(BuildSignalError):
                validate_endpoint(url, True)

    def test_loopback_and_dns_boundary(self):
        validate_endpoint("http://127.0.0.1:11434/v1")
        validate_endpoint("http://[::1]:1234/v1")
        with self.assertRaises(BuildSignalError):
            validate_endpoint("http://localhost.evil.example/v1")

    def test_init_does_not_overwrite(self):
        path = self.directory / "starter.toml"
        self.assertEqual(main(["init", "--path", str(path)]), 0)
        original = path.read_bytes()
        with self.assertRaises(SystemExit):
            main(["init", "--path", str(path)])
        self.assertEqual(original, path.read_bytes())

    def test_collection_filters_pr_and_security(self):
        self.assertEqual(len(self.signals), 5)
        self.assertNotIn("Security report excluded", [s["title"] for s in self.signals])

    def test_future_and_closed_issues_excluded(self):
        base = {"number": 1, "updated_at": "2026-09-08T00:00:00Z"}
        self.assertEqual(normalize("a/b", [base], "issue", NOW, 45), [])
        base.update(updated_at="2026-09-06T00:00:00Z", state="closed")
        self.assertEqual(normalize("a/b", [base], "issue", NOW, 45), [])

    def test_body_bounded_and_url_constructed(self):
        base = {
            "number": 1,
            "body": "x" * 2000,
            "updated_at": "2026-09-06T00:00:00Z",
            "html_url": "javascript:alert(1)",
        }
        signal = normalize("a/b", [base], "issue", NOW, 45)[0]
        self.assertEqual(len(signal["body"]), 1200)
        self.assertEqual(signal["url"], "https://github.com/a/b/issues/1")

    def test_cross_repository_clustering(self):
        groups = cluster(self.signals)
        self.assertEqual(len(groups), 3)
        self.assertEqual(max(len(g["issues"]) for g in groups), 2)

    def test_cluster_ids_and_keywords_are_order_independent(self):
        self.assertEqual(cluster(self.signals), cluster(list(reversed(self.signals))))

    def test_alias_normalization(self):
        self.assertEqual(tokens("Tool calls and tools"), {"tool", "call"})

    def test_score_bounds_and_weights(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1)
        for group in cluster(self.signals):
            value, parts = score(group, NOW, None)
            self.assertTrue(0 <= value <= 100)
            self.assertTrue(all(0 <= x <= 100 for x in parts.values()))

    def test_competition_reduces_score(self):
        group = cluster(self.signals)[0]
        self.assertGreater(
            score(group, NOW, {"total_count": 0})[0], score(group, NOW, {"total_count": 100})[0]
        )

    def test_competition_failure_is_explicit(self):
        with patch.object(self.client, "competition", side_effect=BuildSignalError("unavailable")):
            output, warnings = rank(cluster(self.signals), self.client, self.config, NOW)
        self.assertTrue(warnings)
        self.assertIsNone(output[0]["competition"])
        self.assertEqual(output[0]["components"]["competition_gap"], 50)

    def test_cache_roundtrip_and_corruption(self):
        cache = Cache(self.directory)
        cache.put("key", {"ok": True}, "tag")
        self.assertEqual(cache.get("key")["data"], {"ok": True})
        cache.path("key").write_text("broken")
        self.assertIsNone(cache.get("key"))

    def test_fresh_cache_avoids_network(self):
        calls = []

        def transport(url, **kwargs):
            calls.append(url)
            return 200, {"ETag": "a"}, []

        client = GitHub(Cache(self.directory), token="", transport=transport)
        client.get("/repos/a/b/issues")
        client.get("/repos/a/b/issues")
        self.assertEqual(len(calls), 1)

    def test_stale_etag_304_reuses_data(self):
        cache = Cache(self.directory, ttl=0)
        cache.put("https://api.github.com/repos/a/b/issues", [1], "tag")

        def transport(url, **kwargs):
            self.assertEqual(kwargs["headers"]["If-None-Match"], "tag")
            return 304, {}, None

        client = GitHub(cache, token="", transport=transport)
        self.assertEqual(client.get("/repos/a/b/issues"), [1])

    def test_private_repository_rejected_before_collection(self):
        client = GitHub(
            Cache(self.directory), token="", transport=lambda *a, **k: (200, {}, {"private": True})
        )
        with self.assertRaises(BuildSignalError):
            collect(client, self.config, NOW)

    def test_visibility_is_not_cached(self):
        calls = []

        def transport(*a, **k):
            calls.append(1)
            return 200, {}, {"private": False if len(calls) == 1 else True}

        client = GitHub(Cache(self.directory), token="", transport=transport)
        client.public_repository("a/b")
        with self.assertRaises(BuildSignalError):
            client.public_repository("a/b")

    def test_pagination_stops_at_limit(self):
        calls = []

        def transport(url, **kwargs):
            calls.append(url)
            return 200, {}, [{}] * 100

        client = GitHub(Cache(self.directory), token="", transport=transport)
        self.assertEqual(len(client.items("a/b", "issues", 150, NOW.isoformat())), 150)
        self.assertEqual(len(calls), 2)
        self.assertIn("state=open", calls[0])

    def test_redirects_rejected(self):
        self.assertIsNone(
            NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test")
        )

    def test_model_changes_only_brief(self):
        opportunity = self.opportunity()
        original = copy.deepcopy(opportunity)
        config = DEFAULT["enrichment"] | {"model": "local-test"}
        brief = {
            "problem": "A bounded summary",
            "proposed_v1": ["A fixture validator"],
            "validation": ["Reproduce two linked issues"],
        }

        def transport(url, **kwargs):
            payload = json.loads(kwargs["data"])
            self.assertNotIn('"body"', payload["messages"][1]["content"])
            return 200, {}, {"choices": [{"message": {"content": json.dumps(brief)}}]}

        enrich(opportunity, config, transport)
        self.assertEqual(opportunity["brief"], brief)
        for key in original.keys() - {"brief", "enriched"}:
            self.assertEqual(opportunity[key], original[key])

    def test_invalid_model_output_retains_original(self):
        opportunity = self.opportunity()
        original = copy.deepcopy(opportunity)
        with self.assertRaises(BuildSignalError):
            enrich(
                opportunity,
                DEFAULT["enrichment"] | {"model": "test"},
                lambda *a, **k: (200, {}, {"choices": [{"message": {"content": "{}"}}]}),
            )
        self.assertEqual(opportunity, original)

    def test_report_escapes_html_links_and_table_delimiters(self):
        self.assertNotIn("<script>", escape("<script>"))
        self.assertIn("\\|", escape("a|b"))
        self.assertEqual(safe_url("javascript:alert(1)"), "https://github.com")
        self.assertEqual(safe_url("https://github.com@evil.test/x"), "https://github.com")

    def test_demo_reports_reproducible_and_without_bodies(self):
        opportunities, warnings, paths = run(
            self.config, self.client, NOW, self.directory, demo=True
        )
        before = [p.read_bytes() for p in paths]
        run(self.config, self.client, NOW, self.directory, demo=True)
        self.assertEqual(before, [p.read_bytes() for p in paths])
        payload = json.loads(paths[1].read_text())
        self.assertEqual(len(opportunities), 3)
        self.assertEqual(warnings, [])
        self.assertTrue(payload["demo"])
        self.assertNotIn('"body":', paths[1].read_text())
        self.assertIn("synthetic fixtures", paths[0].read_text())

    def test_cli_demo(self):
        self.assertEqual(main(["demo", "--output", str(self.directory)]), 0)


if __name__ == "__main__":
    unittest.main()
