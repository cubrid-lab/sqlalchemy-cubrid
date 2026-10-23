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

- [ ] I checked existing Assignees, claims and PRs; maintainer-operated autonomous agents taking `good first issue` work have issue-specific approval and assignment. Human-led outside contributors need no preapproval or Assignee rights.
- [ ] The linked issue has current scope, verifiable completion criteria and validation instructions; completed dependencies are not still blockers

- [ ] My code follows the project's code style
- [ ] I have linked required GitHub CI and reported recommended local checks actually run or omitted
- [ ] I have added tests for new functionality (if applicable)
- [ ] I have updated matching behavior/API/version/config documentation, or provided a populated standalone physical source line `Docs: not needed - <reason>` when none is required
- [ ] I have recorded known warnings, limitations and follow-up work

## Review and Final Disposition

<!-- All human/AI contributions follow identical review standards. -->
- Required GitHub CI results at final head: **pending**.
- Recommended local checks performed and results, or reasons not run.
- Optional Oracle/Copilot/agent-review findings: links and dispositions or N/A.
- Findings: fixed + test / rejected with reason / deferred issue.
- Unresolved review threads: details or "none" after final verification.
- Maintainer merge decision: **pending** after final code, required CI and security assessment.
<!-- Maintain independent review for protected compiler/dialect/Alembic,
     CI permissions, and release/publishing changes. AI is advisory. -->

## Validation

<!-- Commands actually executed, results, and checks not run with reasons. -->

Live CUBRID/Alembic evidence (dialect, SQL, reflection or migration changes; CUBRID version and command, or "not applicable"):

<!-- Optional additional AI review: scope/tool/result; advisory only, not test evidence. -->

<!-- If documentation is not required, explain why or request the maintainer-managed `docs-not-needed` label.
     The literal placeholder above and examples inside comments/code/quotes are not valid reasons. -->

<!-- Translation help: name languages and reason. This is a request, not a bypass;
     maintainers explicitly approve the existing translations-deferred label and own follow-up. -->

## Related Issues

<!-- Use Closes #N for a completed LOCAL issue (or N/A and a reason).
     Cite sibling dependencies as Refs owner/repo#N, not closing keywords.
     Each repo manages its own work and closure; the PR title check enforces
     no direct auto-closing references to a foreign repository. -->
