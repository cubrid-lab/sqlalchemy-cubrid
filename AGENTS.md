# AGENTS.md

Project knowledge base for AI coding agents.

## Project Overview

**sqlalchemy-cubrid** is a SQLAlchemy 2.0 dialect for the CUBRID relational database.
It provides SQL compilation, type mapping, schema reflection, DDL/DML extensions,
Alembic migration support, and PEP 561 typing.

- **Language**: Python 3.11+
- **Framework**: SQLAlchemy 2.0 – 2.1
- **License**: MIT
- **Version**: single-sourced from `sqlalchemy_cubrid/__init__.py` → `__version__` (Production/Stable); see [CHANGELOG.md](CHANGELOG.md) for the current release

## Architecture

```mermaid
graph TD
    root["sqlalchemy_cubrid/ (Main package + py.typed)"]
    init["__init__.py - Public API exports types, insert(), merge(), replace(), trace_query(), __version__"]
    compat["_compat.py - SQLAlchemy private API compatibility helpers"]
    base["base.py - CubridExecutionContext, CubridIdentifierPreparer"]
    compiler["compiler.py - CubridSQLCompiler, CubridDDLCompiler, CubridTypeCompiler"]
    dialect["dialect.py - CubridDialect reflection, connection, isolation levels"]
    pycubrid["pycubrid_dialect.py - PyCubridDialect pure Python driver variant"]
    aio["aio_pycubrid_dialect.py - PyCubridAsyncDialect async driver variant"]
    dml["dml.py - ON DUPLICATE KEY UPDATE (Insert), MERGE statement"]
    trace["trace.py - Query tracing helper"]
    types["types.py - CUBRID type system numeric, string, LOB, collection"]
    req["requirements.py - SA 2.0 test requirement flags"]
    alembic["alembic_impl.py - CubridImpl for Alembic migrations"]
    typed["py.typed - PEP 561 marker"]

    root --> init
    root --> compat
    root --> base
    root --> compiler
    root --> dialect
    root --> pycubrid
    root --> aio
    root --> dml
    root --> trace
    root --> types
    root --> req
    root --> alembic
    root --> typed
```

### Module Responsibilities

| Module | Role |
|---|---|
| `dialect.py` | Main dialect class. Handles `create_connect_args`, reflection (`get_columns`, `get_pk_constraint`, `get_foreign_keys`, `get_indexes`, `get_table_comment`, etc.), isolation levels, `import_dbapi()`. |
| `pycubrid_dialect.py` | `PyCubridDialect` — subclasses `CubridDialect` for the pycubrid pure Python driver. Overrides `import_dbapi()`, `create_connect_args()`, `on_connect()`, `do_ping()`, `do_executemany()`, isolation re-apply, and the pycubrid part of disconnect detection (`errno`, client-side messages). |
| `aio_pycubrid_dialect.py` | `PyCubridAsyncDialect` — async pycubrid variant for `create_async_engine()` / `AsyncSession`, registered as `cubrid.aiopycubrid`. Inherits all driver policy from `PyCubridDialect`; adds only the async adapter, pool class and `get_driver_connection()`. |
| `compiler.py` | SQL compilation. `visit_cast`, `limit_clause`, `for_update_clause`, `update_limit_clause`, DDL (`get_column_specification`, `AUTO_INCREMENT`, `COMMENT`), type compilation for all CUBRID types. |
| `dml.py` | Custom DML constructs: `insert()` with `.on_duplicate_key_update()`, `merge()` with `.using()`, `.on()`, `.when_matched_then_update()`, `.when_not_matched_then_insert()`. |
| `types.py` | Type classes: `STRING`, `BIT`, `CLOB`, `SET`, `MULTISET`, `SEQUENCE`, `MONETARY`, `OBJECT`, plus standard type overrides. |
| `base.py` | Execution context (`get_lastrowid`), identifier preparer (lowercase folding, 254-char max, reserved words). |
| `trace.py` | `trace_query()` helper that enables CUBRID tracing around a statement and returns trace output. |
| `requirements.py` | Test requirement flags — marks what CUBRID does/doesn't support for SA's test suite. |
| `alembic_impl.py` | `CubridImpl(DefaultImpl)` with `transactional_ddl = True` (CUBRID DDL rolls back with the transaction); `emit_begin()` emits nothing because CUBRID has no `BEGIN`. Registered by the `alembic.plugins` entry point (`_sqlalchemy_cubrid_alembic.py`) on Alembic 1.18+, or by `dialect.py` importing it on Alembic 1.7.2-1.17 (#595). |
| `_compat.py` | Internal compatibility helpers that wrap SQLAlchemy private APIs used by the dialect/compiler. |

### Entry Points (pyproject.toml)

```toml
[project.entry-points."sqlalchemy.dialects"]
cubrid = "sqlalchemy_cubrid.dialect:CubridDialect"
"cubrid.cubrid" = "sqlalchemy_cubrid.dialect:CubridDialect"
"cubrid.pycubrid" = "sqlalchemy_cubrid.pycubrid_dialect:PyCubridDialect"
"cubrid.aiopycubrid" = "sqlalchemy_cubrid.aio_pycubrid_dialect:PyCubridAsyncDialect"
```

## Development

### Setup

```bash
git clone https://github.com/cubrid-lab/sqlalchemy-cubrid.git
cd sqlalchemy-cubrid
make install          # pip install -e ".[dev]" + pytest-cov + pre-commit + tox
```

### Key Commands

```bash
make test             # Fast offline tests with 95% coverage threshold (-m "not integration and not repo")
make test-repo        # Repository-tooling tests (Makefile, signal handling, repo scripts; -m repo)
make test-offline     # Every offline test (fast + repo) with coverage
make lint             # ruff check + format
make format           # Auto-fix lint/format
make integration      # Run-owned Docker project → integration tests → cleanup
make test-all         # tox across Python 3.11–3.14
```

### Test Commands (manual)

```bash
# Offline (no DB needed) — this is the primary test command (same as `make test`)
pytest test/ -v -m "not integration and not repo" \
  --cov=sqlalchemy_cubrid --cov-report=term-missing --cov-fail-under=95

# Repository-tooling tests (Makefile, signal handling, repo scripts; same as `make test-repo`)
pytest test/ -v -m repo

# Integration (requires Docker)
docker compose up -d
export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"
pytest test/test_integration.py -v
```

### Docker

```bash
docker compose up -d                          # Default version from docker-compose.yml
CUBRID_VERSION=11.4 docker compose up -d      # Specific version
docker compose down -v                        # Cleanup
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
- Test classes: `TestCubridSQLCompiler`, `TestCubridTypes`, etc.
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

Choose the required review route based on the tool that **actually developed**
the change and record it in the PR. A requested review, green CI, self-review,
or an automated "approval recommended" summary is not a completed review.

**OpenCode with Oracle** — for non-trivial work:
1. Obtain an Oracle **pre-implementation design review** before coding.
2. Implement the agreed scope with tests.
3. Update the affected behavior, support and release documentation.
4. Obtain an Oracle **post-implementation code review** of the actual result,
   address material findings, and record both review outcomes and validation.

Trivial OpenCode edits may omit Oracle phases 1 and 4 only with a recorded reason.
The two Oracle reviews satisfy this development route without an additional
automatic requirement for GitHub Copilot. Repository/branch protection,
maintainer approval, and required CI still apply.

**Standalone Claude Code or Codex** — implement, test, document and open a PR;
**wait for a substantive submitted GitHub Copilot review or a review by another
person** before merge. A submitted COMMENTED review containing a real code
assessment counts as review evidence, but not as formal GitHub APPROVED.
Review requests, bot summaries without substantive findings, self-review and
green CI do not satisfy the review requirement. Check accepted fixes at the
final relevant head; if no qualifying review arrives, leave the PR unmerged.

**Human/other contributors** — follow the normal contributor/review process.
Maintainers coordinate internal tools, integration, evidence and release
classification; no external contributor must install OpenCode, Oracle, Claude
Code, Codex or Copilot. Preserve authorship and include tool attribution only
when that tool actually produced the work.

All changes to `main` must go through a reviewed PR; no direct pushes. Broad
review/backlog requests do not authorize assigned or reserved good-first issues.

## Agent PR scope and review guardrails

- Before editing, record one acceptance contract, affected files, explicit non-goals
  and the validation plan. Keep each PR to one independently reviewable change.
  Separate contributor guidance, CI configuration and new validator behavior.
- Triage AI findings against that contract, a supported-environment reproduction
  and impact. AI severity is not authority to add capabilities or widen the contract;
  obtain explicit maintainer direction or defer out-of-scope work to a separate issue.
- Batch accepted fixes locally and run relevant checks before publishing a review
  head. Deduplicate agent-initiated review requests by head SHA and review purpose.
- Default to two published AI review rounds total per scoped PR/task: the initial
  review and one corrective re-review. New commits do not reset this budget.
  Further rounds or scope expansion require explicit maintainer direction.
- If unresolved work needs another round at the limit, stop automatic revisions;
  keep the PR Draft and report incomplete work, blockers and a proposed split.
  Never merge with unresolved critical/security defects or failed required CI.
- Maintain one editable, agent-owned English status comment. Avoid bot mentions in
  routine updates, per-finding progress replies and repeated review requests.
  Preserve contributor history; revisit external PRs only after an author-updated head SHA.

## Review disposition and merge evidence

- Record development route, reviewer or Oracle design/post review evidence,
  reviewed head SHA and pending/complete status in the PR.
- Classify actionable findings as fixed (commit plus focused test), rejected
  (contract/reproduction reason), or deferred (linked issue and rationale).
  A submitted COMMENTED review is not formal APPROVED status.
- Post one **final** disposition reply in each relevant inline thread rather
  than repeated progress messages. A maintainer or reviewer resolves only after
  checking the updated code and evidence. Replies and outdated diffs do not
  automatically resolve a thread; do not bulk-resolve old conversations.
- Keep one editable, agent-owned English PR status comment with overall review
  outcome, required CI, checks not run, and unresolved threads.
- Before merge confirm the route and the final relevant code. Never merge with
  required review still pending, failed required CI, or unresolved
  critical/security findings. Give nonblocking open threads an explicit
  maintainer disposition. Do not change branch protection or auto-merge here.

## Test Structure

Representative core test modules (not exhaustive; list `test/` for the current set,
including repository-tooling, fuzz, differential and Alembic tests):

```
test/
├── conftest.py              # Fixtures: mock dialect, engine, connection
├── test_compiler.py         # SQL compilation (SELECT, JOIN, CAST, LIMIT, DML extensions)
├── test_types.py            # Type system (all type compilations, reflection)
├── test_dialect_offline.py  # Dialect (reflection stubs, connection, isolation)
├── test_base.py             # ExecutionContext, IdentifierPreparer
├── test_requirements.py     # SA requirement flags (parametrized)
├── test_alembic.py          # Alembic CubridImpl import/registry
├── test_dialects.py         # Edge cases
├── test_pycubrid_dialect.py # PyCubridDialect (pure Python driver variant)
├── test_integration.py      # Live DB tests (skipped offline)
└── test_suite.py            # SA test suite runner (skipped offline)
```

### Test Stats

- Large and growing offline and integration suites; exact counts shift with every PR, so see the `offline-tests` / `integration-tests` CI job output for current numbers rather than a hardcoded snapshot here
- Coverage threshold: 95% (CI-enforced, `--cov-fail-under=95` in the `offline-tests` job)
- A handful of defensive fallback branches are intentionally unreachable in normal operation (SA-version-specific compatibility shims, exhaustive-but-unreachable `else` arms); see `--cov=sqlalchemy_cubrid --cov-report=term-missing` output (or `make test`) for current line numbers instead of a pinned list

### Running Tests

Most tests are **offline** — they mock the CUBRID connection and test SQL compilation,
type mapping, and reflection logic without a database. Only `test_integration.py` and
`test_suite.py` need a live CUBRID instance.

## CUBRID-Specific Knowledge

### Key Differences from MySQL/PostgreSQL

- **No RETURNING** — `INSERT/UPDATE/DELETE ... RETURNING` not supported
- **No native BOOLEAN** — mapped to `SMALLINT` (0/1)
- **JSON support (10.2+)** — native JSON type is mapped in this dialect, including path/index helpers and reflection support
- **No ARRAY** — uses `SET`, `MULTISET`, `SEQUENCE` collection types
- **No Sequences** — uses `AUTO_INCREMENT`
- **No multi-schema** — single-schema model
- **No RELEASE SAVEPOINT** — `do_release_savepoint()` is a no-op
- **DDL is transactional** — `ROLLBACK` undoes DDL and DDL never commits earlier DML; only client autocommit (turned off by the dialect) commits it early. `transactional_ddl = True`, so a whole Alembic upgrade is one transaction by default; recommend `transaction_per_migration=True` for long or large-table migrations (uncommitted DDL holds schema locks)
- **3 MVCC isolation levels** — `READ COMMITTED` (default), `REPEATABLE READ`, `SERIALIZABLE`
- **Identifier folding** — lowercase (not uppercase like SQL standard)
- **Max identifier length** — 254 characters

### Connection Format

SQLAlchemy URL: `cubrid://user:password@host:port/dbname`
CUBRID native:  `CUBRID:host:port:dbname:::`

The dialect translates automatically in `create_connect_args()`.

### CUBRID Versions Tested

Supported and tested CUBRID versions are maintained in
[docs/SUPPORT_MATRIX.md](docs/SUPPORT_MATRIX.md); CI lanes are defined in
[docs/CI_POLICY.md](docs/CI_POLICY.md). Tests use Docker images `cubrid/cubrid:{version}`.

## CI/CD

### Workflows

| File | Trigger | Purpose |
|---|---|---|
| `.github/workflows/ci.yml` | PR, main, weekly, manual | Full offline suite on PRs and representative integration; see docs/CI_POLICY.md |
| `.github/workflows/integration-full.yml` | Manual dispatch, release workflow_call | Full supported compatibility matrix |
| `.github/workflows/release-please.yml` | Push to main, manual dispatch | Prepare the release PR; compose generated and curated notes; never publish |
| `.github/workflows/publish-pypi.yml` | Push to main; recovery dispatch (`resume` / `verify-only` / `dry-run`) | Detect a merged release, then matrix, build, tag + GitHub Release + PyPI, cookbook verification, summary |

### CI Matrix

Routine CI is tiered: pull requests run one representative cell, main and
changed-weekly runs cover the oldest/newest supported Python and CUBRID endpoints,
and the full integration matrix runs only on manual dispatch and every release
(no automatic nightly full matrix). The exact cells, change classification and
gate requirements live in [CI policy](docs/CI_POLICY.md); check it rather than
copying versions here.

## Documentation Map

| File | Content |
|---|---|
| `README.md` | Concise landing page |
| `docs/CONNECTION.md` | Connection strings, URL format, driver setup |
| `docs/TYPES.md` | Full type mapping, CUBRID-specific types |
| `docs/ISOLATION_LEVELS.md` | The three CUBRID MVCC isolation levels |
| `docs/DML_EXTENSIONS.md` | ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT, TRUNCATE |
| `docs/ALEMBIC.md` | Alembic migration guide, limitations, workarounds |
| `docs/FEATURE_SUPPORT.md` | Feature comparison with MySQL, PostgreSQL, SQLite |
| `docs/DEVELOPMENT.md` | Dev setup, testing, Docker, coverage, CI/CD |
| `docs/ORM_COOKBOOK.md` | Practical ORM usage examples with CUBRID |
| `docs/PRD.md` | Product requirements document |
| `CHANGELOG.md` | Release history (Keep a Changelog format) |
| `CONTRIBUTING.md` | Contribution guidelines |
| `SECURITY.md` | Security vulnerability reporting |
| `docs/DRIVER_COMPAT.md` | CUBRID-Python driver versions and known issues |
| `docs/SUPPORT_MATRIX.md` | Supported Python, SQLAlchemy, CUBRID and driver versions |
| `docs/CI_POLICY.md` | CI tiers, selected cells and gate requirements |
| `docs/PERFORMANCE.md` | Performance measurements and benchmark pointers |
| `ROADMAP.md` | Current roadmap (public) |
| `docs/TROUBLESHOOTING.md` | Common issues, error solutions, debugging techniques |

## Issue specification and ownership

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
- Set the actual implementer in GitHub Assignees before implementation.
  Comments alone do not replace assignment. Preserve existing contributor
  claims and open PRs; agree a handoff before changing ownership. If assignment
  permission is missing, request maintainer assignment before starting.
  Broad "review", "fix" or "release preparation" instructions do not override an
  existing contributor assignment.
- On handoff, update Assignees; unassign when returning unfinished work.
  Preserve a contributor's evidence and scope when editing their issue.
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

- Unclaimed: `good first issue`.
- A PR is opened for it: remove `good first issue`, add `status: in progress`.
- PR merged: the issue closes.
- PR closed without merging: first check that no other open PR still addresses the issue. Only if none remains, remove `status: in progress` and restore `good first issue`; otherwise keep it in progress.
- Keep at least 3 genuinely unclaimed good first issues per repository; a good first issue should have a small blast radius and an existing pattern or reference PR to follow, not just a small diff.
- Reserved for newcomers: a maintainer-run agent must not implement an issue labelled
  `good first issue` unless a maintainer authorizes that **specific issue**. Broad
  backlog, review, fix or release-preparation instructions are not authorization.
  Before a release blocker is handed to an agent, a maintainer must check the issue's
  Assignees, comments and open PRs and record the decision on the issue.

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
matrix → build → tag/Release/PyPI → cookbook verification (the cookbook smoke test
called as a pinned reusable workflow, no token) → summary on its own.
Freeze release PRs with `autorelease: review` before editing candidate notes; wait
for preparation to finish and start required PR CI on the final head. Curated
main Unreleased notes are preserved during regeneration; branch-only edits
require the freeze.
Ordinary PRs never change `__version__` or date a CHANGELOG section. Never push
tags or publish by hand; the only manual entry point is the narrow recovery
dispatch of `publish-pypi.yml`. Procedure, failure matrix and recovery:
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

## Performance Context

sqlalchemy-cubrid provides ORM-level validation that pycubrid driver improvements reach
the application layer. Current benchmark results and methodology live in
[docs/PERFORMANCE.md](docs/PERFORMANCE.md) and
[cubrid-benchmark](https://github.com/cubrid-lab/cubrid-benchmark); current priorities live
in [ROADMAP.md](ROADMAP.md) (public) and the
[CUBRID Ecosystem Roadmap](https://github.com/orgs/cubrid-lab/projects/2) board (org
members only), not here.
