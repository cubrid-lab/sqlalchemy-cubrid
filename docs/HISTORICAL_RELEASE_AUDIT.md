# Historical GitHub Release inventory — 2026-11-07

This inventory was read from the GitHub Releases API and the current `CHANGELOG.md` after PR #1152 merged. It is a **read-only audit**. No GitHub Release bodies, tags, dates, assets, or draft states were changed.

## Scope

- GitHub Release objects: **37**
- Published releases: **28**
- Draft releases: **9** — `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.3.1`, `v0.3.2`, `v0.4.0`, `v0.5.0`, `v0.6.0`, `v0.7.0`
- Canonical changelog also contains `0.0.1`, which has no corresponding GitHub Release object. Do not create a release just for formatting.
- The previously mentioned count of 37 *published* releases was incorrect: it includes 9 drafts. Drafts must not be published or modified as part of a public-release migration.

## Published release audit

Body and changelog character counts are indicators of scope, **not** proof of semantic equivalence. `Different` can reflect legitimate GitHub-only comparison links, formatting, or substantial content drift.

| Version | GitHub body chars | Changelog section chars | Full Changelog | Has byline | Body vs section |
|---|---:|---:|---|---|---|
| v1.12.2 | 2,071 | 1,342 | Yes | No | Different |
| v1.12.1 | 3,439 | 3,343 | Yes | No | Different |
| v1.12.0 | 3,149 | 3,053 | Yes | No | Different |
| v1.11.7 | 515 | 419 | Yes | No | Different |
| v1.11.6 | 410 | 314 | Yes | No | Different |
| v1.11.5 | 83,821 | 83,725 | Yes | No | Different |
| v1.11.0 | 39,144 | 39,048 | Yes | No | Different |
| v1.10.0 | 11,328 | 11,327 | No | No | Same |
| v1.9.0 | 77,352 | 77,351 | No | No | Same |
| v1.8.0 | 57,883 | 57,882 | No | Yes | Same |
| v1.7.1 | 21,114 | 21,113 | No | No | Same |
| v1.7.0 | 17,223 | 17,755 | No | No | Different |
| v1.6.0 | 1,646 | 2,154 | No | No | Different |
| v1.5.1 | 614 | 761 | Yes | No | Different |
| v1.5.0 | 2,705 | 2,331 | No | No | Different |
| v1.4.3 | 736 | 770 | Yes | No | Different |
| v1.4.2 | 91 | 475 | Yes | No | Different |
| v1.4.1 | 192 | 594 | No | No | Different |
| v1.4.0 | 1,580 | 1,553 | No | No | Different |
| v1.3.0 | 1,174 | 2,416 | Yes | No | Different |
| v1.2.3 | 949 | 471 | No | No | Different |
| v1.2.2 | 1,419 | 1,397 | No | No | Different |
| v1.2.1 | 654 | 478 | Yes | No | Different |
| v1.2.0 | 2,256 | 997 | No | No | Different |
| v1.1.0 | 1,056 | 518 | Yes | No | Different |
| v1.0.0 | 1,609 | 1,249 | Yes | No | Different |
| v0.8.0 | 1,335 | 649 | Yes | No | Different |
| v0.7.1 | 742 | 522 | No | No | Different |

## Review and migration gates

1. Create an immutable local backup of every **published** GitHub Release body and its metadata using `scripts/audit_historical_releases.py --output-dir <new-empty-directory>`. Keep the backup outside the repository and review its report. Never overwrite an earlier snapshot.
2. Start with `v1.12.2` (source curated in #1152), then proceed in descending version order. Handle very large releases such as `v1.11.5` and `v1.9.0` in smaller review batches; do not auto-reflow them.
3. For each entry, cross-check real PR author and merged commit evidence. Use `by @username` only when verified, and first-contribution wording only after a complete earlier merged-PR search. Omit uncertain credits.
4. For each version, review the original body against its canonical changelog section, including every Markdown link, bullet continuation, issue marker and semantic claim. Run the wrapping checks and view rendered Markdown.
5. Make historical `CHANGELOG.md` changes in a reviewed PR. After approval, synchronize only the corresponding published GitHub Release body. Before writing, re-fetch and compare with the exact backup to avoid overwriting concurrent edits.
6. Keep all draft releases in Draft status. Preserve original titles, tags, publication timestamps, prerelease status, attached assets and package artifacts.
7. Record completed versions and evidence in [issue #1153](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1153). Do not claim a version has been migrated until its GitHub Release body is verified.

## Rollout

After completing and validating the SQLAlchemy repository, adapt the same rules and safety gates to `pycubrid`, `cubrid-client`, then `cubrid-mcp-server`. Keep each repository's native release automation.
