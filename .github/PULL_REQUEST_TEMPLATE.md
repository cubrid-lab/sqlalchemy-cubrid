<!--
Title: `type: description` or `type(scope): description`; add `!` before the colon
for a breaking change. Types: feat, fix, docs, test, perf, refactor, ci, build,
chore, style, revert. English, lowercase start unless the first word is an API
name, acronym, or proper noun. No trailing period, no issue numbers (put
"Closes #123" in Related Issues). The title becomes the squash commit title.
See CONTRIBUTING.md#pull-request-and-commit-titles.
-->
## Summary

<!-- Brief description of changes -->

## Changes

<!-- List the specific changes made -->

-

## Type of Change

<!-- Check the relevant option -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change; add `!` to the title)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Chore (maintenance, dependencies, CI, etc.)

## Checklist

- [ ] The implementation issue has the actual owner in Assignees; existing claims and PRs were coordinated
- [ ] The linked issue has current scope, verifiable completion criteria and validation instructions; completed dependencies are not still blockers

- [ ] My code follows the project's code style
- [ ] I have recorded executed `make check-all` / `make test` / `make test-repo` / `make test-offline` results and reasons for any unexecuted checks
- [ ] I have added tests for new functionality (if applicable)
- [ ] I have updated matching behavior/API/version/config documentation, or provided a populated standalone physical source line `Docs: not needed - <reason>` when none is required
- [ ] I have recorded known warnings, limitations and follow-up work

## Review Route and Final Disposition

<!-- For maintainer/agent-authored PRs; no tool requirement for external contributors. -->
- Development route: OpenCode + Oracle pre/post / standalone Claude Code / standalone Codex / human/other (select one).
- Review evidence: reviewer or Oracle references, reviewed head SHA, or **pending**.
- Finding dispositions: fixed commit + verification / rejected with reason / deferred issue.
- Unresolved review threads and reason, or "none verified".
- Maintainer merge decision: applicable review completed; final code and required CI checked.
<!-- Requested reviews, green CI, and automated "approval recommended" text alone do not count. -->

## Validation

<!-- Commands actually executed, results, and checks not run with reasons. -->

Live CUBRID/Alembic evidence (dialect, SQL, reflection or migration changes; CUBRID version and command, or "not applicable"):

<!-- Optional AI review: scope/tool/result. AI review is separate from executed checks. -->

<!-- If documentation is not required, explain why or request the maintainer-managed `docs-not-needed` label.
     The literal placeholder above and examples inside comments/code/quotes are not valid reasons. -->

<!-- Translation help: name languages and reason. This is a request, not a bypass;
     maintainers explicitly approve the existing translations-deferred label and own follow-up. -->

## Related Issues

<!-- Closes #123 / Refs #456. Issue numbers go here, not in the PR title. -->
