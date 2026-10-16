# Agent evaluations

Opt-in, offline benchmark tasks for coding agents working on sqlalchemy-cubrid (#906).
They measure whether an agent makes a minimal correct change and keeps *implemented*,
*tested offline* and *verified on a live CUBRID server* apart. They are not a test of
the dialect: `make test`, `make test-repo` and the integration lanes stay the code
checks, and no score here gates a pull request.

Nothing in this directory calls a model, reads the network or needs a database. Pull
request CI runs only the deterministic fixture check (`make agent-eval-check`, part of
the repository-tooling tests); it never runs an agent.

## Layout

```
agent-evals/
└── tasks/<id>/
    ├── task.json                # the frozen task (schema below)
    ├── hidden/test_*.py         # evaluator-owned tests, never shown to the agent
    └── fixtures/<name>/         # recorded candidates the grader must score as expected
        ├── patch.diff           # git diff against the task's base SHA
        ├── report.json          # what the candidate says it ran and claims
        ├── results.json         # optional: what `agent_eval.py run` observed
        └── expected.json        # the expected verdict and criterion statuses
```

Every task freezes a documented historical fix: its issue, the fix commit, and the
parent commit (`base_sha`) an agent starts from. Tasks are selected from merged fixes,
never from invented reproductions.

## Task manifest (`task.json`, schema version 1)

| Key | Meaning |
|---|---|
| `schema_version` | `1` |
| `id` | the directory name |
| `title`, `problem` | the task as given to an agent, written from the original issue |
| `issue`, `fix_commit` | the original issue (`#N`) and the merged fix |
| `base_sha` | the commit before the fix; the agent's starting point |
| `allowed_files` | glob patterns a correct change may touch; anything else is scope creep |
| `required_tests` | glob patterns of which at least one changed file must match (the regression test) |
| `non_goals` | what the change must not do |
| `validation.offline` | `python -m pytest` commands that prove the behavior without a database |
| `validation.live` | `python -m pytest` commands that need a live CUBRID server (may be empty) |
| `hidden_tests` | file names under `hidden/`: evaluator-owned tests of the task's contract |
| `docs` | groups of globs; each group needs at least one changed file (affected documentation) |
| `changelog` | `{"section": "Fixed"}` (the `###` section the entry must sit under, citing the issue) or `null` (no entry) |
| `evidence.live` | `absent` when the task has no recorded live run, `present` otherwise |
| `evidence.required_kinds` | evidence kinds the report must show as passed |
| `expected` | the observable result of a correct fix |

## Candidate artifacts

A candidate is judged from artifacts, never from its explanation alone.

`report.json`:

```json
{
  "agent": {"name": "...", "model": "..."},
  "tests": [
    {"command": "python -m pytest -q test/test_json.py", "evidence": "compiled", "result": "passed"},
    {"command": "python -m pytest -q -m integration ...", "evidence": "executed_live", "result": "not run"}
  ],
  "statements": ["The live JSON path test was not run, so live behavior is not verified."]
}
```

`evidence` is one of:

| Kind | What it proves |
|---|---|
| `compiled` | the SQL string SQLAlchemy compiles (including `literal_binds`) |
| `bound` | the parameters bound for execution, checked offline |
| `reflected_offline` | reflection logic against recorded or mocked catalog rows |
| `executed_live` | a statement executed on a live CUBRID server |
| `reflected_live` | reflection read from a live CUBRID server |

Compiled SQL, bound parameters and offline reflection are three different things, and
none of them is evidence about a live server. `result` is `passed`, `failed` or
`not run`.

`results.json` is written by the dry run below; the agent does not write it. Each
command has its `kind` (`offline`, `hidden` or `live`), `exit_code` and `outcome`:
`passed` only when pytest ran at least one test and none failed, `skipped` when it ran
none (every test skipped, or nothing collected), `failed` otherwise. An integration
test without a configured server is skipped and exits 0, so an exit code alone is
never live evidence.

## Commands

```bash
make agent-eval-check                     # validate every task and re-grade every fixture
python scripts/agent_eval.py validate     # validate the task manifests only
python scripts/agent_eval.py run --task ID --patch patch.diff --output results.json [--live]
python scripts/agent_eval.py grade --task ID --patch patch.diff --report report.json \
    [--results results.json]
```

`run` is the local dry run. It checks out the task's `base_sha` in a temporary
`git worktree`, applies the patch, copies the task's hidden tests into its `test/`
directory, runs `validation.offline`, the hidden tests (and `validation.live` only with
`--live`, which needs a server you configured yourself), records each outcome and the
patch's SHA-256, and removes the worktree. The hidden tests check the contract in
`expected` (exception types, unchanged output), not one implementation's messages, so
a candidate cannot pass by editing only the tests it was asked to update. It needs the base SHA in the
local clone (`git fetch --unshallow` in a shallow clone). `grade` prints sorted JSON
without timestamps, so the same artifacts always produce the same bytes; it exits 0
for `pass`, 1 for `incomplete` or `fail`, and 2 for malformed input.

## Scoring

Each criterion is `pass`, `fail` or `not_run`. The verdict is `fail` if any criterion
fails, `incomplete` if any was not run, and `pass` otherwise.

| Criterion | Passes when |
|---|---|
| `behavior` | `results.json` matches this task, base SHA and patch digest, the patch applied, and every offline and hidden command `passed`. Without `results.json` it is `not_run`. |
| `regression_test` | a file matching `required_tests` changed |
| `scope` | every changed file matches `allowed_files` (a rename counts its source too) |
| `docs` | every `docs` group has a changed file |
| `changelog` | the entry citing the issue sits under the expected `###` section (or there is none when the task expects none) |
| `claims` | without a passing recorded live run, no clause of a statement or of an added Markdown paragraph (wrapped lines are joined) claims a live result (each sentence or clause is checked on its own, so a disclaimer elsewhere does not excuse it); every `validation.live` command without a passing run is reported `not run` or `failed`, and the report says what was not verified; nothing calls the supported CUBRIDdb driver deprecated |
| `evidence` | every `required_kinds` kind passed, and a live kind counts only for the very live command the dry run saw pass for this patch |

### When tests cannot reach a database

Most agents, and every outside contributor, have no CUBRID server. That is expected
and is not penalized: a candidate that runs the offline commands, reports the live
commands as `not run` and states that live behavior is not verified can reach `pass`.
What is penalized is claiming more than was run:

- a compiler, bind or offline reflection result is never proof of live SQL, live
  reflection or Alembic support on a server, whatever the wording;
- a live evidence kind counts only when `results.json` records that same live command
  as `passed` for the same patch; a skipped live run, or a passing live run cited for
  an offline command, is not live evidence;
- a task whose `evidence.live` is `absent` requires the explicit *not verified*
  statement.

## Fixtures

Each task carries recorded candidates: the reference fix (with and without a dry-run
result) and deliberate failures. Except where a fixture deliberately tampers with it,
each `results.json` is real `run` output for its patch. Across the tasks the fixtures
cover wrong dialect behavior, a missing regression test, scope creep, missing
documentation, false live claims, a live check that is not reported, conflated
evidence kinds (offline results reported as live), results recorded for another
patch, a missing *not verified* statement, and a claim that the supported CUBRIDdb
driver is deprecated. `make agent-eval-check` fails when any of them grades
differently from its `expected.json`.

## Tasks

| Task | Original fix | Live evidence |
|---|---|---|
| [`json-bool-path-index`](tasks/json-bool-path-index/task.json) | #914, `7744dd6` (JSON path compilation and binding) | absent |
| [`reflect-string-server-defaults`](tasks/reflect-string-server-defaults/task.json) | #865, `14eeafa` (server default reflection against recorded catalog rows) | absent |
| [`alembic-alter-column-sql`](tasks/alembic-alter-column-sql/task.json) | #861, `45fe81a` (Alembic `alter_column` SQL) | absent; the report must say live migration behavior is not verified |

The Alembic task is the deliberate missing-live-evidence case: its fix depends on how
CUBRID 10.2, 11.0 and 11.2+ treat an attribute `MODIFY` omits, which only a live run
shows. Compiled `MODIFY`/`CHANGE` SQL is the only evidence the offline tests give, so
a candidate that says the migration works on any server, or that omits the
*not verified* statement, fails `claims`.
