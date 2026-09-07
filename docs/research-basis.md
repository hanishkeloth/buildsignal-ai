# Research basis and scope

BuildSignal's product hypothesis is that unresolved issue demand can help developers choose useful
projects before implementation. Trending repositories reveal existing adoption; public issue trackers
provide a different signal: requests and failures developers are already experiencing.

This is a hypothesis, not proof of uniqueness or commercial demand. The repository does not claim to
cover every recent AI technology. It provides an inspectable research workflow for agent and local-AI
ecosystems. Its bundled example uses fictional repositories and synthetic issues.

## Primary implementation references

- [GitHub issue endpoints](https://docs.github.com/en/rest/issues/issues): issue collection can also
  return pull requests, so BuildSignal excludes the `pull_request` key explicitly.
- [GitHub release endpoints](https://docs.github.com/en/rest/releases/releases): release metadata supplies
  ecosystem activity context. Drafts are excluded.
- [GitHub REST best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api):
  conditional requests and serial request behavior inform the ETag cache and sequential client.
- [GitHub search API](https://docs.github.com/en/rest/search/search): repository search supports lexical
  competition discovery, with separate rate limits and incomplete-result caveats.

Consulted for reconstruction on 7 September 2026. These sources support the API behavior, not the
validity of the product hypothesis or a calibrated score. No measured customer adoption is claimed.

## Competing approaches to evaluate

Before implementing a ranked idea, check existing directories, issue-management systems, repository
analytics, semantic issue clustering tools, and research agents. Keyword search alone is insufficient.
Review maintained alternatives' actual behavior and issue trackers. Prefer contributing to an existing
project when it already solves the problem.

The intended distinction is the combination of cross-repository unresolved requests, deterministic
ranking, visible competition checks, optional local-only brief enrichment, and reproducible offline
fixtures. That combination must be validated with users; it is not asserted to be globally unique.
