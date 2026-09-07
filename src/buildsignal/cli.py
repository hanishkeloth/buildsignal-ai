"""Command-line pipeline with a reproducible offline demonstration."""

import argparse
import json
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from .analysis import WEIGHTS, collect, date, rank, cluster
from .config import BuildSignalError, load_config
from .github import Cache, GitHub
from .report import enrich, write_reports


class FixtureClient:
    def __init__(self, path):
        try:
            self.data = json.loads(Path(path).read_text())
            if not isinstance(self.data, dict) or not isinstance(self.data["repositories"], dict):
                raise ValueError()
        except (OSError, ValueError, KeyError):
            raise BuildSignalError("Invalid fixture file") from None

    def public_repository(self, name):
        if self.data["repositories"].get(name, {}).get("private") is not False:
            raise BuildSignalError(f"Missing or non-public fixture repository: {name}")

    def items(self, name, kind, limit, since=None):
        return self.data["repositories"][name].get(kind, [])[:limit]

    def competition(self, keywords):
        return {"query": " ".join(keywords[:3]), "total_count": 0, "repositories": []}


def run(config, client, as_of, output, *, competition=True, use_model=False, demo=False):
    signals = collect(client, config, as_of)
    opportunities, warnings = rank(
        cluster(signals, config["scan"]["threshold"]), client, config, as_of, competition
    )
    if use_model:
        for item in opportunities:
            try:
                enrich(item, config["enrichment"])
            except BuildSignalError as exc:
                warnings.append(str(exc))
    paths = write_reports(opportunities, config, as_of, warnings, output, demo)
    return opportunities, warnings, paths


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find evidence-backed AI project opportunities")
    parser.add_argument("--version", action="version", version="buildsignal 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a starter TOML configuration")
    init.add_argument("--path", default="buildsignal.toml")
    demo = commands.add_parser("demo", help="run synthetic offline fixtures")
    demo.add_argument("--output", default="demo-report")
    scan = commands.add_parser("scan", help="scan configured public repositories")
    scan.add_argument("--config", default="buildsignal.toml")
    scan.add_argument("--output", default="reports")
    scan.add_argument("--cache-dir", default=".cache/buildsignal")
    scan.add_argument(
        "--as-of", help="ISO timestamp; filters current data, not a historical snapshot"
    )
    scan.add_argument("--fixture")
    scan.add_argument("--no-competition", action="store_true")
    scan.add_argument("--enrich", action="store_true")
    commands.add_parser("explain-score", help="print score weights")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            with Path(args.path).open("x", encoding="utf-8") as stream:
                stream.write(files("buildsignal").joinpath("default.toml").read_text())
            print(f"Created {args.path}")
            return 0
        if args.command == "explain-score":
            print(json.dumps(WEIGHTS, indent=2))
            return 0
        is_demo = args.command == "demo"
        if is_demo:
            config = load_config(files("buildsignal").joinpath("demo.toml"))
            client = FixtureClient(files("buildsignal").joinpath("demo.json"))
            as_of = date("2026-09-07T00:00:00Z")
        else:
            config = load_config(args.config)
            client = FixtureClient(args.fixture) if args.fixture else GitHub(Cache(args.cache_dir))
            as_of = date(args.as_of) if args.as_of else datetime.now(UTC)
        opportunities, warnings, paths = run(
            config,
            client,
            as_of,
            args.output,
            competition=is_demo or not args.no_competition,
            use_model=not is_demo and (args.enrich or config["enrichment"]["enabled"]),
            demo=is_demo or bool(getattr(args, "fixture", None)),
        )
        for path in paths:
            print(f"Wrote {path}")
        print(f"Opportunities: {len(opportunities)}; warnings: {len(warnings)}")
        return 0
    except (BuildSignalError, OSError, ValueError) as exc:
        parser.exit(2, f"buildsignal: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
