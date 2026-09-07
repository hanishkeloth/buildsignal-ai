# Security policy

BuildSignal reads public GitHub data and optionally sends bounded metadata to an explicitly configured
model endpoint. It does not execute source code, issue text, release instructions, or model commands.

## Boundaries

- Repository visibility is checked without a cache before collection; private repositories are refused.
- The GitHub origin is fixed. Authorization headers are never logged and redirects are rejected.
- Model endpoints require numeric loopback by default; remote access requires explicit opt-in and HTTPS.
- Model requests ignore environment proxies and reject redirects to avoid unintended destinations.
- Model output must pass a bounded schema. Ranking and evidence cannot be edited by the model.
- Markdown escapes untrusted markup. Bodies are omitted from JSON and Markdown reports.
- Cache files contain public API responses including bodies; treat the cache as potentially sensitive
  if a public issue is later edited or removed. Do not commit or share it automatically.
- Exact sensitive labels are excluded. This is not a complete detector of confidential material.

Visibility can change after verification; the check is not a transactional guarantee. GitHub labels and
public status do not guarantee absence of personal data. Review generated reports before sharing.
An opted-in remote model receives public issue titles and repository identifiers, which may still be
sensitive in context. Do not use production credentials in examples or tests.

## Reporting

For a non-sensitive reproducible defect, open an issue. For a vulnerability involving credentials or
private data, use GitHub's private vulnerability reporting if enabled. Otherwise open a minimal issue
asking for a private contact channel without including exploit details, credentials, or personal data.

Version 0.1.x is the currently supported release line. This is alpha software; no security audit claimed.
