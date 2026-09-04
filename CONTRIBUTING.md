# How work happens in this repository

Two agents share this workspace: **Claude Code** and **Codex**. The owner reviews and merges.

## The workflow, without exception

1. **Never write to `main`.** Create a task branch: `claude/<short-slug>` or `codex/<short-slug>`.
2. Open a **draft pull request** as soon as the branch has a first commit, with a plain-language
   description of what changes and why.
3. The owner reviews and merges. Agents do not merge their own work.
4. Rebase on `main` before asking for review. Resolve conflicts on the branch.
5. If you hit merge conflicts you cannot resolve confidently, **stop and say so**. Do not force, do
   not cherry-pick around it, do not rewrite history.

## Before opening a pull request

- [ ] Tests pass locally (`pytest`)
- [ ] `ruff check` and `ruff format --check` pass
- [ ] Nothing in `docs/decree-356-boundaries.md` is violated
- [ ] No secret, no customer document, no real personal data in the diff
- [ ] Anything touching money or document counts has a test
- [ ] `SETUP.md` / `RUNBOOK.md` updated if the owner's steps changed
- [ ] The PR description says what the owner should run to see it working

## Commit messages

Say what changed and why in plain English. Reference the ADR if there is one.

## Two agents, one repository

Take separate branches. If both are working, the second to start rebases. Never edit the same file in
two live branches without saying so in both pull requests.

An agent may make the minimum change outside its assigned lane when that change is required to make
CI green on its own branch. The pull request must name the out-of-lane file, explain why the change
was necessary, and call it out for the owner's review.
