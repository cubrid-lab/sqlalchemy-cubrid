# AGENTS.md

Project knowledge base for AI coding agents.

## Project Overview

**sqlalchemy-cubrid** is a SQLAlchemy 2.0 dialect for the CUBRID relational database.
It provides SQL compilation, type mapping, schema reflection, DDL/DML extensions,
Alembic migration support, and PEP 561 typing.

- **Language**: Python 3.11+ (`requires-python = ">=3.11"`)
- **Framework**: SQLAlchemy 2.0 – 2.1 (`sqlalchemy>=2.0,<2.2`)
- **Supported versions**: Python, SQLAlchemy, CUBRID and driver versions are maintained in
  [docs/SUPPORT_MATRIX.md](docs/SUPPORT_MATRIX.md); `pyproject.toml` owns dependency bounds
- **License**: MIT
- **Version**: single-sourced from `sqlalchemy_cubrid/__init__.py` → `__version__` (Production/Stable); see [CHANGELOG.md](CHANGELOG.md) for the current release

## Task Routing

Every section of this file applies to every change. Task-specific detail lives in the
guides under `docs/agents/`, listed in the table below. Agent tools load this file but not
the documents it links, so open the guide for your task before editing. The guides are
English-only contributor guidance: `scripts/check_docs_translation.py` checks only the pages
directly under `docs/`, and `scripts/check_agents_docs.py` checks their links and commands.
`pyproject.toml` owns dependency bounds and [docs/SUPPORT_MATRIX.md](docs/SUPPORT_MATRIX.md)
owns supported versions and driver status.

| Task | Read before editing | Run before review |
|---|---|---|
| Compiler and DML (SQL compilation, `insert().on_duplicate_key_update()`, `merge()`, DDL) | [Dialect guide](docs/agents/dialect.md), [Architecture guide](docs/agents/architecture.md), [Code Conventions](#code-conventions), [docs/DML_EXTENSIONS.md](docs/DML_EXTENSIONS.md) | `make test`, `make check` |
| Reflection and types | [Dialect guide](docs/agents/dialect.md), [Architecture guide](docs/agents/architecture.md), [docs/TYPES.md](docs/TYPES.md) | `make test`, `make check`, `make integration` |
| Alembic migrations | [Dialect guide](docs/agents/dialect.md) (transactional DDL), [Architecture guide](docs/agents/architecture.md), [docs/ALEMBIC.md](docs/ALEMBIC.md) | `make test`, `make check`, `make integration` |
| pycubrid drivers and async | [Architecture guide](docs/agents/architecture.md), [docs/CONNECTION.md](docs/CONNECTION.md), [docs/DRIVER_COMPAT.md](docs/DRIVER_COMPAT.md), [docs/SA_COMPAT.md](docs/SA_COMPAT.md) | `make test`, `make check`, `make integration` |
| Tests and CI workflows | [Testing and CI guide](docs/agents/testing-ci.md), [docs/CI_POLICY.md](docs/CI_POLICY.md), [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | `make verify` |
| Documentation and support claims | [Documentation guide](docs/agents/documentation.md), [Documentation definition of done](#documentation-definition-of-done), [docs/SUPPORT_MATRIX.md](docs/SUPPORT_MATRIX.md) | `python scripts/check_support_claims.py`, `python scripts/generate_llms_full.py`, `python scripts/check_docs_links.py`, `python scripts/check_agents_docs.py` |
| Release | [Release Process](#release-process), [GitHub Release Policy](#github-release-policy), [RELEASING.md](RELEASING.md) | `make release-check VERSION=x.y.z` (read-only; never release by hand) |
| Performance and roadmap | [Performance guide](docs/agents/performance.md), [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | the measurement steps in docs/PERFORMANCE.md |

## Development

### Setup

```bash
git clone https://github.com/cubrid-lab/sqlalchemy-cubrid.git
cd sqlalchemy-cubrid
make install          # pip install -e . --group dev (PEP 735 groups, pip >= 25.1) + pre-commit hooks
```

### Key Commands

```bash
make doctor           # Fail unless the required tools are installed at their pinned versions
make test             # Every offline test (fast + repo) with 95% coverage threshold (-m "not integration")
make test-fast        # Fast offline tests only (-m "not integration and not repo")
make test-repo        # Repository-tooling tests (Makefile, signal handling, repo scripts; -m repo)
make lint             # ruff check (never modifies files)
make format-check     # ruff format --check (never modifies files)
make format           # Auto-fix lint/format (the only mutating target)
make typecheck        # mypy
make check            # lint + format-check + typecheck + security + check-docs-reason
make verify           # check + test (no Docker)
make integration      # Run-owned Docker project → integration tests → cleanup (INTEGRATION_DRIVER=pycubrid|cubriddb)
make integration-local # Integration tests against an already-running CUBRID (set CUBRID_TEST_URL)
make test-all         # tox (envlist in tox.ini)
```

### Test Commands (manual)

```bash
# Fast offline lane (no DB needed; same as `make test-fast`)
pytest test/ -v -m "not integration and not repo" \
  --cov=sqlalchemy_cubrid --cov-report=term-missing --cov-fail-under=95

# Repository-tooling tests (Makefile, signal handling, repo scripts; same as `make test-repo`)
pytest test/ -v -m repo

# Integration (requires a live CUBRID; `make integration` manages Docker for you)
docker compose up -d
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"  # cubrid:// needs CUBRIDdb
pytest test/ -v -m integration
```

### Docker

```bash
make docker-up                                # Default version, broker on 127.0.0.1:33000
CUBRID_VERSION=11.4 make docker-up            # Specific version
CUBRID_TEST_PORT=33300 make docker-up         # Another host port (CUBRID_PORT is deprecated)
make docker-down                              # Stop and remove; keeps the test data volumes
make docker-clean                             # Stop and delete the test data volumes
```

## Code Conventions

### Style

- **Linter/Formatter**: Ruff
- **Line length**: 100 characters
- **Target Python**: 3.11+
- **Imports**: `from __future__ import annotations` in every module
- **Type hints**: Full typing; PEP 561 compliant (`py.typed`)
- **super()**: Always `super().__init__()`, never `super(ClassName, self)`

### Naming

- Classes: `CubridDialect`, `CubridSQLCompiler`, `CubridTypeCompiler`, `CubridDDLCompiler`
- Test classes: `TestSelectCompilation`, `TestCubridTypes`, etc.
- Test files: `test/test_*.py`

### Patterns to Follow

- All SA dialect methods use `@cache_anon_map` / `@reflection.cache` where appropriate
- Reflection methods accept `**kw` and use `text()` for parameterized queries (no f-string SQL)
- Type compiler methods: `visit_TYPENAME(self, type_, **kw)` returning SQL string
- `supports_statement_cache = True` — required for SA 2.0

### Anti-Patterns (Never Do)

- No `as any`, `@ts-ignore` equivalents — no type suppression
- No f-string interpolation in SQL queries (SQL injection risk)
- No `super(ClassName, self)` — use `super()` only
- No Python 2 constructs (`basestring`, `getargspec`, etc.)
- No empty `except` blocks

## Development Workflow (cubrid-lab org standard)

Every contribution follows the **same review criteria**, whether implemented
by a person, OpenCode, Codex, Claude Code, ChatGPT, Copilot, or another tool.
No particular AI reviewer or pre/post-review sequence is a prerequisite.
See [CONTRIBUTING.md](CONTRIBUTING.md) for this repository's validation commands.

1. **Scope and implement:** keep the PR focused, add relevant tests, update
   affected documentation, and identify unrun checks and remaining risks.
2. **GitHub CI:** use required GitHub Actions checks as the authoritative
   validation of the final PR head, including lint, unit, integration/live,
   security, docs and release checks wherever applicable. Local checks are
   encouraged but are not an additional mandatory merge gate.
3. **Code review:** examine functionality, tests, security, regression risk,
   and maintainability. Oracle, Copilot and `agent-review` are optional,
   **advisory** inputs—not approval or alternate gates based on coding tool.
4. **Final decision:** address or disposition findings, verify the final
   source and required CI, and leave merging to the responsible maintainer.
   Preserve independent approval for high-risk security, CI permissions
   and release/publishing paths under existing project safeguards.

Do not weaken branch protections, live CUBRID checks, protected code paths,
security constraints or release/publishing controls through a documentation
simplification.

## Agent PR scope and review guardrails

These guardrails apply regardless of the implementation tool:
- Define the acceptance criteria, affected files, non-goals and validation
  before substantial implementation; keep changes independently reviewable.
- Evaluate review findings against reproduced behavior, risk and impact.
  AI-generated severity labels alone never justify scope expansion.
- Fix verified issues and run relevant checks on the final code state.
  AI review rounds are optional; avoid duplicate review requests and bot spam.
- Maintain contributor credit and preserve existing PR discussion history.
  For external contributions, request a new review after the author updates
  the relevant head.
- Do not merge unresolved critical/security defects or failed required CI.

## Review disposition and merge evidence

- Record the tested head, required GitHub CI results, checks not run,
  remaining risks, reviewer findings and maintainer merge decision.
- Resolve each actionable finding by a focused fix plus verification,
  a reasoned rejection, or an explicitly tracked follow-up. Maintain
  separate handling for confidential security findings.
- Add one final reply per relevant inline thread. Reviewers/maintainers
  confirm the updated code before marking threads resolved; a reply,
  outdated diff or bot verdict is not proof of resolution.
- Keep one concise, editable status comment when automated agents assist.
  Treat Oracle, Copilot and `agent-review` output as optional context only.
- The responsible maintainer checks the final relevant head, required CI
  and any independent high-risk approval before merging.

## PR overlap and execution order

- **Before opening a PR:** check the linked issue's current decision and
  dependencies, relevant open PRs, and changes merged into `main` since the
  branch was created. Overlapping filenames call for review, not automatic
  rejection. In the PR, name relevant `Supersedes #N`, `Depends on #N`, or
  `Parallel to #N` relationships, with a brief reason; otherwise say `None`.
- **Select a canonical implementation:** compare the accepted behavior, scope,
  validation, and maintainer decision. Neither the newest PR nor the lowest
  issue number automatically wins. Do not merge a narrower, outdated policy
  after a more complete, incompatible replacement has landed.
- **Before merging:** repeat the overlap and dependency check against current
  `main` and other open PRs. A green check or an AI recommendation does not
  override an unresolved design decision, an incompatible release boundary,
  protected-path approval, or a blocking finding.
- **When policy changes:** inspect open issue descriptions, open PRs and
  contributor-facing templates for contradictory instructions. Update the
  active work and explain any superseded plan during the same review cycle;
  otherwise record an explicit, narrowly scoped follow-up.
- **After merging:** the responsible maintainer reconciles linked issues and
  competing open PRs in the same review cycle. Comment and close a truly
  superseded PR with a link to its replacement; if independent work remains,
  explain why and update its scope. Coordinate with external contributors,
  retain their history, and do not close a parent issue until its own acceptance
  criteria are satisfied.
- **Priority is not merge readiness:** `priority: critical`, `priority: high`,
  `priority: medium`, or `priority: low`
  on an issue records urgency and impact; `size:` records effort. Choose the
  next *executable* PR based on issue priority, satisfied dependencies, risk,
  validation, and maintainer release decisions. A high-priority blocked issue
  may need a decision before code, while an independent lower-priority PR can
  proceed. Neither creation date nor PR number determines execution order.
  Record exceptional reprioritization with a reason in the relevant issue.

This is a maintainer workflow, not another CI gate or a request for duplicate
status checks, bots, or cross-repository trackers.

## Issue specification and ownership

Issues and implementation acceptance are repository-local: file work in the
repository whose code, workflow, or documentation must change. Each repository
owns its scope, priority, assignee, validation, release decision and closure.
Every issue must be understandable without opening another repository's issue.
When several repositories need changes, create a separate, self-contained issue
and PR in each repository. Never use an issue here as an organization-wide
tracker, a shared implementation contract or an approval gate for other projects.
Link another repository's issue only when its concrete technical behavior is
essential evidence for local reproduction or verification; do not cross-link
implementation issues by default or inherit another repository's acceptance
criteria, ownership or closure requirements.

Before publishing or editing an issue, inspect its title and full body:
- Describe this repository's problem, evidence, affected files and actual Make
  targets, expected behavior and checkable completion criteria.
- Exclude contest/judging, assessment, submission, presentation rehearsal,
  evaluation-tag/SHA freezes and event-timed implementation gates. Commit or
  release identifiers belong only where needed to reproduce technical behavior.
- Do not invent `make spec-*` targets, assume a sibling project's commands apply
  here or prescribe a universal command/report format without checking this
  repository's Makefile and CI.
- Search for duplicate issues and conflicting target semantics before posting;
  reread the saved title/body and correct misplaced scope or references.
Never use issue auto-closing keywords with another repository's issue; its
maintainer controls closure. The existing required PR title check rejects
direct foreign-repository closing references in the PR body, the PR title and
commit messages while allowing Refs links. `main` is squash-merged with the PR
title and the commit messages; an edit to the squash message at merge time is
not checked, so do not add foreign closing keywords there.

An issue body is the current work specification, not a session transcript.
Before implementation, maintainers/agents must ensure it states the problem
and impact, evidence with a revision/environment, reproducible steps or the
investigation question, expected behavior, scope/non-goals, relevant files,
verifiable completion criteria, validation method and actual dependencies.
Say "not verified" when evidence is missing; never invent a reproduction,
server result, release availability or test command. Small docs tasks need
only the applicable fields. Research issues close on a recorded decision;
implementation follows the agreed contract.

- Keep priority/size in canonical labels and execution order in the backlog
  tracker. Do not prepend repeated triage banners to individual issue bodies.
- Put dated progress, pause/resume instructions and review outcomes in issue
  comments. Keep historical reproductions and source links in the body with
  their original revision/date and clear evidence limits.
- Reconcile completed work and closed dependencies when scope changes, a
  related PR merges, work is handed over or the issue is closed. Closed work
  is reference evidence, not a blocker. A merged upstream PR is not proof
  that a compatible release is available.
- For maintainer-operated autonomous agents and internally assigned work, maintainers must set the actual implementer in GitHub Assignees before implementation. Comments alone are not a substitute for this agent assignment; autonomous agents also need explicit issue-specific authorization to take a `good first issue`.
- Human-led outside contributors (including those using AI assistance under their direction) may work on an unclaimed issue and open a PR without prior approval or Assignee permissions. Check active assignments, comments, and PRs; an interest comment is encouraged but optional. Do not silently take over another contributor's claimed work.
- Maintainers own assignment updates, handoffs and issue labels; preserve contributor evidence and coordinate release-blocker handoffs.
- Before saving an issue edit, check for contradictory current statuses,
  stale dependency/checklist entries, duplicate criteria and unproven claims.
  Re-read the issue after saving. Never mark a tracker complete just because
  its children merged; confirm its integration acceptance separately.

## Issue Labeling (cubrid-lab org standard)

For maintainer/agent-managed issue creation in **any cubrid-lab repository**, assign exactly one
`priority: <value>` label and exactly one `size: <value>` label at creation time,
alongside a type label (`bug`/`enhancement`/`documentation`/`chore`/`ci`/…) and an
`area:` label when applicable. These must be GitHub labels, not just text in the
issue title or body.

Maintainers and triagers own label policy and apply or create the canonical GitHub
labels. Authorized agents filing or triaging on their behalf apply the same
canonical labels. Outside reporters do not need label-write permission: they can
describe urgency and effort, but those descriptions help triage and do not
themselves assign a label.

Issue titles use the same `type(scope): description` format as pull request
titles (see [CONTRIBUTING.md](CONTRIBUTING.md#pull-request-and-commit-titles)).
`.github/workflows/issue-triage.yml` flags incomplete human-submitted issue
titles or labels as `status: needs triage` without posting a comment or
guessing priority/size. Maintainers remove that label once triage is complete.
Agents and workflows creating issues through CLI/API must supply canonical
metadata at creation; `GITHUB_TOKEN`-created issues do not retrigger this guard.

Use the following exact names, with **one space after the colon**:

- Priority: `priority: critical`, `priority: high`, `priority: medium`, `priority: low`.
- Size: `size: XS`, `size: S`, `size: M`, `size: L`, `size: XL`.

Do not introduce variants such as `priority:high`, `priority-high`, `P1`, or
`size:S`. Reuse the repository's canonical labels; if a required label is missing,
create it with the exact name above before filing the issue. This policy governs
new issue creation, not bulk renaming or relabeling existing issues unless
explicitly requested.

Priority reflects urgency and impact; size estimates implementation effort and
helps contributors pick appropriately scoped work.

| Label | Meaning | Rough guide |
|-------|---------|-------------|
| `size: XS` | Trivial change | < ~10 lines; single-file typo/config/one-liner |
| `size: S` | Small change | One file or one focused function; a single test or doc page |
| `size: M` | Medium change | A few files; a new test module, a bug fix with tests, a CI job |
| `size: L` | Large change | Cross-cutting change across many files; multi-artifact (e.g. demo GIF + video + docs) |
| `size: XL` | Very large | Consider splitting into smaller issues before starting |

Rules:

1. **Size reflects effort, not importance** — a one-line fix for a critical bug is still `size: XS`.
2. **Maintainers, triagers and authorized agents filing for them assign both `priority:` and `size:` when filing.** If scope or impact
   is uncertain, use a provisional estimate, explain the uncertainty in the body,
   and add `status: needs triage`. External reports may start with that label;
   refine estimates during maintainer triage.
3. **`good first issue` should be `size: XS` or `size: S`.** If a good-first-issue grows
   past `size: S`, re-scope it or drop the `good first issue` label.
4. **`size: XL` is a signal to split**, not a green light to start a sprawling change.

### Good first issue lifecycle

- **Human-led community contributors, including people directing AI-assisted code:** an unassigned `good first issue` is open for participation. They may start and submit a PR without prior maintainer authorization, GitHub Assignee permissions, or internal agent tooling.
- Before starting, check existing Assignees, comments, and open PRs. An interest comment is welcome but optional; it is neither an approval requirement nor an exclusive reservation. Coordinate before overlapping or taking over claimed work.
- **Maintainer-operated autonomous coding agents:** require explicit maintainer authorization for that specific newcomer-reserved issue and an actual GitHub assignment before implementation. A general request to clear backlog or prepare a release is not authorization.
- Maintainers handle Assignees and labels. Human contributors without assignment rights may still submit PRs; ordinary CI and review gates remain mandatory.
- Unclaimed: retain `good first issue`.
- On opening a PR: maintainers remove `good first issue` and add `status: in progress`, coordinating ownership.
- On merge: close the issue. If a PR closes unmerged: check for other open PRs before restoring `good first issue` and removing `status: in progress`.
- Keep at least three genuinely unclaimed XS/S good first issues with a small blast radius and an existing reference pattern.
- A release-blocker handoff to an autonomous agent needs a recorded maintainer decision after checking Assignees, comments and open PRs.

## Documentation definition of done

Any change that affects public behavior, compatibility, installation, configuration, APIs, supported versions, error handling, or SQL/dialect behavior MUST update the matching documentation in the **same PR**. At minimum keep in sync: `CHANGELOG.md`, the relevant files under `docs/` (e.g. `FEATURE_SUPPORT.md`, `ISOLATION_LEVELS.md`, `TYPES.md`), the `SUPPORT_MATRIX.md`, and version/compatibility claims in `README*`.

If no documentation change is needed, state the reason explicitly in the PR body as `Docs: not needed - <reason>` or apply the `docs-not-needed` label. This is enforced by the `docs-sync` CI check.

The body reason must be a populated standalone physical source line, not a placeholder or an
example in quoted/code/comment text. Maintainers control GitHub label exceptions.
Requesting translation help in a PR body grants no exemption: the existing
`translations-deferred` label requires explicit maintainer approval and a recorded
follow-up. Korean-required checks and other-language advisory checks remain intact.

Do not mark work complete until code, tests, and documentation are consistent.

Driver terminology: CUBRIDdb built from cubrid-python v11.3.0.51+ is the
supported official C-extension driver. Recommend pycubrid for new projects,
but describe the `[cubrid]` / `[cubriddb]` installation extras (which select an
untested old PyPI package) as deprecated, not the supported driver itself.
Keep valid historical uses of “legacy,” such as CAS error-code formats.

For README, support/driver/connection guides, PRD, packaging and release-note
changes, review these distinctions before publishing: official vs recommended vs
deprecated; compiled vs reflected vs bound vs returned; implemented vs tested vs
supported; current policy vs dated evidence; and per-driver/version results vs
blanket claims. Check existing issues and PRs first. Package metadata owns current
dependency bounds. CI configuration and recorded runs identify tested combinations.
Tests and recorded runs provide evidence for observed behavior and feature limits. Reviewed
support docs own driver recommendations and deprecation policy. Update the canonical
English source, then any affected Korean counterpart and generated `llms*.txt` output.
The maintainer changing a support policy updates its targeted consistency checks
and regression cases in the same review; semantic support claims still
need linked test/run evidence or an explicit untested qualifier in the PR body.

## Commit Convention

Issue titles, pull request titles and commit subjects follow
[CONTRIBUTING.md - Pull request and commit titles](CONTRIBUTING.md#pull-request-and-commit-titles):
`type(scope)!: description` with types `feat`, `fix`, `docs`, `test`, `perf`,
`refactor`, `ci`, `build`, `chore`, `style`, `revert`; English, lowercase start
unless the first word is an API name, acronym, or proper noun; no trailing
period, no issue numbers in pull request titles (use `Closes #N` /
`Refs #N` in the body). Pull requests are squash-merged and the pull request
title becomes the commit title. The `PR title` check enforces it.

### Format

```
<type>(<scope>): <imperative summary of WHAT changed>

- <bullet 1: specific change with file/function context>
- <bullet 2: ...>

Closes #<issue>

Ultraworked with [Sisyphus](https://github.com/code-yeongyu/oh-my-opencode)
Co-authored-by: Sisyphus <clio-agent@sisyphuslabs.ai>
```

The tool-attribution example applies only to work produced with that tool.
Preserve actual contributor authorship and real coauthors; outside contributions
do not require a named agent, tool credit or a blanket coauthor trailer.

### Rules (MANDATORY)

1. **Subject line describes WHAT changed, not batch/phase labels.**
   - ❌ `fix: batch 4 correctness fixes for 1.0 readiness`
   - ✅ `fix: preserve TZ reflection, STRING national kwarg, and UPDATE LIMIT 0`
2. **Be specific — name the function, type, or behavior.**
   - ❌ `feat: gap fixes, stability messaging, code quality improvements`
   - ✅ `fix: FK actions regex, Alembic guardrails, FULL JOIN/LATERAL rejection`
3. **One logical change per commit.** If subject needs "and" more than once, split.
4. **Never use internal jargon** (batch N, phase N, readiness) — commit history is public.
5. **Type must match content:**
   - `feat` = new capability that didn't exist before
   - `fix` = something was broken and is now correct
   - `refactor` = code moved/restructured but behavior unchanged
   - Don't label a fix as `feat` or a mixed bag as `feat`
6. **Body bullets reference issue numbers** (`#135`, `#136`) for traceability.
7. **Scope is optional** but use it for module-specific changes: `fix(compiler):`, `feat(types):`.
8. **Version in commit message must match actual project version.** Check `sqlalchemy_cubrid/__init__.py` → `__version__`; never reference a stale or placeholder version.

## Release Process

Maintainers own release/tag/publication actions and repository credentials.
Contributors provide the change and validation evidence through the normal PR path.

Version is single-sourced from `sqlalchemy_cubrid/__init__.py` → `__version__ = "x.y.z"`
(`pyproject.toml` reads it dynamically). Merging a reviewed release PR is the only
normal way to release: `release-please.yml` opens it (dated CHANGELOG section +
version bump, checked by `make release-check VERSION=x.y.z`), and after the
squash-merge `publish-pypi.yml` detects the version change and runs consistency → full
matrix → build → candidate verification (the cookbook smoke test in candidate mode on
the built wheel; `publish` needs it) → tag/Release/PyPI → cookbook verification (the
cookbook smoke test called as a pinned reusable workflow, no token) → summary on its own.
Freeze release PRs with `autorelease: review` before editing candidate notes; wait
for preparation to finish and start required PR CI on the final head. Curated
main Unreleased notes are preserved during regeneration; branch-only edits
require the freeze.
Ordinary PRs never change `__version__` or date a CHANGELOG section. Never push
tags or publish by hand; the only manual entry point is the narrow recovery
dispatch of `publish-pypi.yml`. A `last-release-sha` override is temporary:
Prepare release stops once a later release containing it is verified, and a
normal PR must remove it (never edit it away inside a release PR). Procedure, failure matrix and recovery:
[`RELEASING.md`](RELEASING.md).

## GitHub Release Policy

These rules add to the release procedure above; the procedures and gates in
`RELEASING.md` stay authoritative.

### Titles

- A Release title equals its tag exactly. Stable tags and titles are `vMAJOR.MINOR.PATCH`.
- No package name, feature, date or suffix in a title (not `sqlalchemy-cubrid 1.2.3`,
  `v1.2.3 — Foo`, `v1.2.3 (corrected)` or `Release v1.2.3`). Drafts follow the same rule.
- Never move, delete or recreate a tag to fix a title. Never delete and recreate a
  published Release.
- Metadata edits keep the notes, assets, published state and prerelease state. When
  editing a draft through the API, always resend `tag_name`: a PATCH without it resets
  the draft's tag to `untagged-…`. `gh release edit` resends `tag_name` automatically;
  raw `gh api` PATCHes must include it.
- Automation enforces these rules: `publish-pypi.yml` creates Releases with
  `--title "$TAG"` and, on resume or recovery, fails closed through
  `scripts/check_release_title.py` when an existing Release has another title. It never
  renames one. Agents verify these rules whenever they touch release automation.

### Stale drafts

- Inspect drafts before preparing a release. Never assume a draft is pending.
- Classify each draft against its tag and the PyPI history:
  - Already shipped (tag and PyPI version both exist): publish it with
    `make_latest=false`, or remove it, only after maintainer approval.
  - Never shipped: never publish it. Delete it only after maintainer approval.
- Never delete drafts automatically. Preserve their notes and assets.

### Release notes

- `CHANGELOG.md` is the single source of truth. The Release body is the extracted
  CHANGELOG section plus one `**Full Changelog**` compare link
  (`scripts/extract_release_notes.py`).
- Allowed `###` sections, in this order, only when they have content: Upgrade notes,
  Added, Changed, Deprecated, Removed, Fixed, Security, Performance, Documentation, CI,
  Tests. `scripts/lint_changelog.py` enforces this for `[Unreleased]` and for releases
  after 1.10.0.
- Use `Documentation`, not `Docs`. Put release automation and tooling entries under
  `CI` or `Changed`.
- Never bulk-rewrite historical notes or regenerate them from current `main`. A
  selective fix needs a dry-run diff and maintainer approval. Never invent PR or commit
  references. Note formatting never changes tags, dates, artifacts or publish state.
