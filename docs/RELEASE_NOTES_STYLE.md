# Release notes style

The public GitHub Release is for users, not a raw copy of the commit history.
Apply these conventions to this repository and, after review, to other CUBRID Lab
projects without replacing each project's actual publication workflow.

## Standard layout

The GitHub Release title must be exactly the tag (for example, v1.12.3).
The body has a one- or two-sentence user-impact summary followed by only the
applicable standard level-three headings, in the repository's established order:

1. Upgrade notes
2. Added
3. Changed
4. Deprecated
5. Removed
6. Fixed
7. Security
8. Performance
9. Documentation
10. CI
11. Tests

Close with exactly one Full Changelog comparison link. Omit empty sections.
Summaries and details must not claim that a database feature or driver is
unsupported merely because a particular test run failed.

## Changes and authors

- State the observable change, affected component and user impact, not only
  the Conventional Commit subject. Merge overlapping curated/generated entries.
- Use a genuine pull request link when available, not an issue URL disguised as
  a PR. Never imply a reference issue was automatically closed.
- After an entry, credit a *verified* contributing PR author using
  "by @username". Credit eligible co-authors after reviewing the PR and commit
  evidence. Do not infer authorship from an issue author, assignee or commenter.
- For the author's first merged contribution to this repository, use
  "by @username (first contribution 🎉)" if earlier merged PR history has
  been checked. Omit the celebration if the check is inconclusive.
- Treat organization members and outside contributors alike for authorship.
  Do not credit automation bot accounts as human contributors.
- Do not add a separate Contributors or New Contributors heading. Credits
  belong beside the changes they explain. A release with no verifiable author
  credit remains valid.

Example (fictional contributors and PR IDs):

### Fixed

- **Connections** — Corrected reconnect handling (PR #123) by @alice.
- **Types** — Fixed integer conversion (PR #124) by @bob (first contribution 🎉).

### Documentation

- **Examples** — Clarified setup instructions (PR #125) by @charlie.

## Release Please and review

The preparation workflow keeps release-please-generated
RELEASE_CHANGELOG.md unchanged. It decorates an ephemeral copy of generated
entries using the commit-to-merged-PR GitHub API and a query for earlier merged
PRs, then composes CHANGELOG.md. An unverified or ambiguous author is omitted,
not invented. Human-reviewed curated entries can include a byline directly.
A maintainer still reviews the resulting release PR for duplicate entries,
accuracy, migration guidance, author and co-author credits, and actual first
contribution evidence. No release may be published just to exercise formatting.

## Historical releases

One-time retrospective formatting is allowed only as a separately reviewed
migration, not as a new release or a regenerated historical changelog from
current code. Inventory all published Releases and preserve an exact backup
of every original body; require a per-version before/after diff and a verified
author-evidence record. The historic date, tag, title, prerelease state, assets
and package artifacts must remain unchanged.

CHANGELOG.md remains the canonical source. Curate historical sections in a
reviewed PR first, preserving the original technical facts and release dates.
Only after that PR is merged may its approved sections be synchronized to the
corresponding published GitHub Release bodies, one version at a time with
remote-body concurrency checks. Never silently overwrite an externally edited
Release body or claim all history has been updated after only preparing a PR.
