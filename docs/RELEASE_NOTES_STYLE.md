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

## Reader-focused length

Keep the standard headings above rather than adding separate `Highlights` or
`Contributors` sections. For a primarily maintainer-led project, one clear
summary and readable change entries are more useful than a second, separately
maintained release-note format.

- Start with one or two sentences about changes a user can notice or actions
  they may need to take. Put compatibility, security, migration and breaking
  behavior in the appropriate standard sections, especially Upgrade notes.
- Lead each entry with the observable result, then explain why it matters.
  Prefer a short paragraph over a list of implementation steps, internal
  identifiers or every changed helper. Add essential limitations and commands
  when users need them; do not enforce a fixed word or bullet limit.
- Keep `Added`, `Changed`, `Fixed`, `Documentation`, `CI`, `Tests`
  and the other established categories whenever they contain real changes.
  Documentation and test contributors deserve the same accurate attribution
  as runtime-code contributors.
- Credit each verified human PR author or co-author **beside the change**,
  retaining first-contribution markers when proven and direct PR/commit links.
  Condensing duplicate changes must not drop a participating contributor.
  A separate contributor list is not required.
- For unusually large releases, retain important version-specific caveats,
  upgrade instructions and traceable source references. Link supporting
  technical details to their actual PRs or documentation, but do not bury
  actionable warnings or replace release notes with raw commit logs.
- Make the edited `CHANGELOG.md` section the single publication source.
  Review rendered Markdown and cross-check its contributor credits and links
  against the previous notes before editing an existing GitHub Release body.

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
  Reserve `by @username` and `(first contribution 🎉)` for verified **human** contributors. Exclude AI agents, automated assistants, service accounts, and bots even when their GitHub account type is `User`; never guess whether an ambiguous account is human. Human PR authors remain eligible when they use AI tools to assist their work. Keep AI/tool provenance in PR or commit metadata instead of listing the tool as a release-note author.
- Do not add a separate Contributors or New Contributors heading. Credits
  belong beside the changes they explain. A release with no verifiable author
  credit remains valid.

Example (fictional contributors and PR IDs):

### Fixed

- **Connections** — Corrected reconnect handling (PR #123) by @alice.
- **Types** — Fixed integer conversion (PR #124) by @bob (first contribution 🎉).

### Documentation

- **Examples** — Clarified setup instructions (PR #125) by @charlie.

## Markdown line wrapping

Do not hard-wrap or mechanically reflow inline links, issue references,
attribution phrases or backtick-delimited identifiers. Markdown may soft-wrap a
sentence, but a wrapped continuation must remain part of the same bullet.

In particular, a bare issue marker such as "#123" or "# 123" must never start
its own physical line. Prior MkDocs rendering treated such lines as headings.
Prefer full Markdown issue/PR links within the same logical change entry.
Do not split Markdown link labels or destinations across lines, insert an
unintended two-space hard break, or place a "by @username" credit on a separate
line. Use "scripts/check_release_note_wrap.py" against each release candidate
after composing CHANGELOG.md and run its regression tests.

## Release Please and review

The preparation workflow keeps release-please-generated
RELEASE_CHANGELOG.md unchanged. It decorates an ephemeral copy of generated
entries using the commit-to-merged-PR GitHub API and a query for earlier merged
PRs, then composes CHANGELOG.md. An unverified or ambiguous author is omitted,
not invented. Human-reviewed curated entries can include a byline directly.
The composer drops a generated entry whose pull request or referenced issue a
curated entry already cites, unless it credits a contributor the curated entry
does not. A change curated under an issue whose generated entry carries only an
unrelated pull request number cannot be matched automatically.
A maintainer still reviews the resulting release PR for duplicate entries,
accuracy, migration guidance, author and co-author credits, and actual first
contribution evidence. No release may be published just to exercise formatting.

## Credit review checklist

Check these points on every release candidate, and on any change to a released
section. They come from the 2026-11 audit of all published notes (#1220).

1. Map each change entry to the pull request or commit that implements it, and
   credit that PR's human author. An issue number is not a PR: find the PR that
   closed the issue.
2. Credit a co-author only for a verified human account with a substantive
   commit. A commit that only merges `main`, resolves a `CHANGELOG.md` conflict
   or reformats does not make its author a co-author.
3. Never credit an agent or bot, including agent co-author trailers and agent
   commit accounts. When an agent wrote every commit on a branch, credit the
   human who opened and drove the PR.
4. Upgrade notes and highlights that summarize credited entries stay
   uncredited, and so do automated dependency updates.
5. Add `(first contribution 🎉)` only after checking the author's earlier merged
   PRs in this repository.
6. Check that every implementing commit is inside the release's tag range on
   GitHub, not only in a local tag, which can be stale. An entry whose change
   shipped in another version belongs in that version's section.

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
