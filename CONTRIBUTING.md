# Contributing

Start with a reproducible issue and a narrowly scoped proposal. Useful contributions improve evidence
quality, normalization, failure handling, scoring evaluation, or real developer workflows.

Run `python -m pip install -e '.[dev]'`, `ruff check .`,
`python -m unittest discover -s tests -v`, and `python -m build` before opening a pull request.
Tests must run offline; add synthetic fixtures rather than copied personal data.

Preserve deterministic output for identical inputs. Keep runtime dependencies at zero unless a proposed
dependency has a clear, reviewed benefit. Model enrichment must never alter scores or evidence.
Document scoring changes, migration effects, and limitations. Do not add keys, telemetry, automatic
repository execution, hosted-account requirements, or undisclosed remote requests.

Contributions are accepted under the repository's MIT License.
