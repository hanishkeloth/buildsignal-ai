# BuildSignal AI opportunity report

Evidence cutoff: 2026-09-07 | Window: 45 days

> DEMO: synthetic fixtures. These are not real issue reports or market evidence.

> Rankings are deterministic heuristics, not market validation. Local-model briefs require human review.

| Rank | Score | Opportunity | Issues | Repositories |
| ---: | ---: | --- | ---: | ---: |
| 1 | 86.59 | Tool calls returned as plain text | 2 | 2 |
| 2 | 68.75 | Stable tool catalog ordering for prompt cache | 1 | 1 |
| 3 | 64.8 | Need per\-request memory metrics | 1 | 1 |

## Tool calls returned as plain text

Score: 86.59/100

| Component | Value | Weight |
| --- | ---: | ---: |
| demand | 100 | 28% |
| breadth | 50 | 18% |
| recency | 95.51 | 18% |
| evidence | 100.0 | 12% |
| competition gap | 100.0 | 16% |
| release momentum | 55 | 8% |

### Evidence

- [Tool call plain text parsing is inconsistent](https://github.com/example/agent-runtime/issues/10) (example/agent\-runtime; issue; updated 2026-09-04)
- [Tool calls returned as plain text](https://github.com/example/local-server/issues/1) (example/local\-server; issue; updated 2026-09-06)
- [Tool call schema validation](https://github.com/example/local-server/releases) (example/local\-server; release; updated 2026-09-05)

### Competition

Query: call text tool. Matches: 0 (lexical, not exhaustive).

### Proposed scope

Brief source: deterministic template

Tool calls returned as plain text

- Reproduce the linked issues with deterministic fixtures\.
- Implement one narrow workflow that resolves the repeated friction\.
- Compare maintained competitors before committing to scope\.

### Validation

- Validate the need with affected maintainers\.
- Publish a runnable before/after example\.

## Stable tool catalog ordering for prompt cache

Score: 68.75/100

| Component | Value | Weight |
| --- | ---: | ---: |
| demand | 62.38 | 28% |
| breadth | 25 | 18% |
| recency | 95.48 | 18% |
| evidence | 100.0 | 12% |
| competition gap | 100.0 | 16% |
| release momentum | 20 | 8% |

### Evidence

- [Stable tool catalog ordering for prompt cache](https://github.com/example/agent-runtime/issues/11) (example/agent\-runtime; issue; updated 2026-09-05)

### Competition

Query: cache catalog prompt. Matches: 0 (lexical, not exhaustive).

### Proposed scope

Brief source: deterministic template

Stable tool catalog ordering for prompt cache

- Reproduce the linked issues with deterministic fixtures\.
- Implement one narrow workflow that resolves the repeated friction\.
- Compare maintained competitors before committing to scope\.

### Validation

- Validate the need with affected maintainers\.
- Publish a runnable before/after example\.

## Need per\-request memory metrics

Score: 64.8/100

| Component | Value | Weight |
| --- | ---: | ---: |
| demand | 48.28 | 28% |
| breadth | 25 | 18% |
| recency | 95.48 | 18% |
| evidence | 100.0 | 12% |
| competition gap | 100.0 | 16% |
| release momentum | 20 | 8% |

### Evidence

- [Need per\-request memory metrics](https://github.com/example/local-server/issues/2) (example/local\-server; issue; updated 2026-09-05)

### Competition

Query: memory metrics need. Matches: 0 (lexical, not exhaustive).

### Proposed scope

Brief source: deterministic template

Need per\-request memory metrics

- Reproduce the linked issues with deterministic fixtures\.
- Implement one narrow workflow that resolves the repeated friction\.
- Compare maintained competitors before committing to scope\.

### Validation

- Validate the need with affected maintainers\.
- Publish a runnable before/after example\.

## Limits

- Demand reflects public issue activity, not willingness to pay.
- Search absence does not establish originality; review competitors manually.
- Clustering is lexical and can merge unrelated issues or miss paraphrases.
- Only the highest preliminary-scoring clusters receive competition checks.
- Bodies are omitted from both reports; API response caches contain public bodies.
