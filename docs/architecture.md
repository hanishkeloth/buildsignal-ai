# Architecture

`config.py` validates TOML and endpoint policy. `github.py` implements GET-only GitHub collection,
bounded responses, ETag revalidation, search pacing, and atomic cache replacement. Repository metadata
is never cached, so a visibility change is checked before each collection pass.

`analysis.py` normalizes and deduplicates signals, applies label/time filters, performs title-weighted
union-find clustering, and calculates transparent component scores. Stable IDs derive from sorted issue
IDs. Competition queries use the three most frequent weighted keywords. Only the top 2N preliminary
clusters receive searches to limit API costs; results may not be the global top N after competition.

`report.py` optionally validates a model-written brief and emits escaped Markdown plus structured JSON.
Neither report includes issue bodies. `cli.py` composes the pipeline and provides `init`, `scan`, `demo`,
and `explain-score`. There is no daemon, database, hidden agent execution, or model requirement.

Scores are bounded heuristics. Breadth saturates at four repositories; demand uses log engagement;
recency decays with a 30-day half-life; competition uses an inverse log count; release momentum counts
keyword-related releases. Evidence measures body length, labels, and engagement, not factual truth.

Clustering is O(n²), with up to 30 repositories and 500 issue rows each. Large configured scans can be
slow and should use smaller caps. Union-find is transitive, so intermediary issues may bridge topics.
Search counts include potential false matches and the watched repositories themselves.
