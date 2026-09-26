# Jarvis Git Fabric

Status: clean-room architecture  
Owner: Charles Earl Lipshay  
Purpose: Git graph, repository operations, multi-forge compatibility, and AI-assisted diagnostics.

## Why this name

“GitBit” is already used by unrelated software products. Jarvis Git Fabric avoids product confusion and describes the broader goal: unify local Git operations, remote hosting services, coding agents, CI, diagnostics, and portfolio governance without copying proprietary products.

## Product layers

### 1. Git Graph Workbench

A visual graph for commits, branches, tags, remotes, worktrees, merge bases, changed files, and repository health.

Safe read operations are available by default. Commit, push, rebase, cherry-pick, tag changes, branch deletion, reset, and history rewriting require a preview plus approval. Force push and destructive reset remain disabled by default.

### 2. Universal Forge Adapter

Normalize GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, Forgejo, and generic Git remotes into shared objects:

- repository;
- branch and tag;
- commit;
- work item;
- pull or merge request;
- pipeline/workflow;
- release;
- artifact;
- review and approval.

Each adapter declares its supported operations, authentication type, permissions, rate limits, webhooks, and verification state. Unsupported operations fail closed.

### 3. Coding Engine

AI Jarvis routes bounded implementation tasks to Codex, GitHub Copilot, or another approved provider. Every provider works on an isolated branch or worktree and returns a structured receipt.

### 4. Diagnostic Engine

The engine correlates:

- Git diff and history;
- failing tests and build logs;
- compiler, linter, and type-checker output;
- dependency and secret scans;
- CI status;
- runtime logs, traces, and health checks;
- independent model reviews.

Deterministic evidence outranks model opinion.

### 5. Change Safety Engine

Before a risky Git operation, generate:

- exact command or API action;
- affected repository and refs;
- commits/files at risk;
- backup or recovery reference;
- predicted conflicts;
- validation steps;
- rollback plan;
- required approval.

### 6. Portfolio Control Tower

Across the repository portfolio, report documentation, tests, CI, security, stale branches, open changes, release readiness, product role, revenue role, and website eligibility. Private project details never enter public dashboards without explicit approval.

## GitBit-like capabilities to implement cleanly

The first personal version may include:

- topological commit graph;
- commit and changed-file inspector;
- side-by-side diffs;
- branch, tag, remote, and worktree views;
- safe branch creation and switching;
- cherry-pick and squash previews;
- conflict detection;
- rebase planning;
- dropped-commit recovery references;
- repository search;
- AI explanations of history and diffs;
- diagnostic correlation between commits and failures.

Do not copy another product’s branding, interface assets, proprietary behavior, documentation, or source unless its license explicitly permits reuse and all license obligations are followed.

## Execution roadmap

### Phase 1 — read-only graph

Build a local read-only Git graph and normalized repository model. Test with synthetic repositories containing branches, merges, tags, rebases, and conflicts.

### Phase 2 — safe mutations

Add branch creation, commits, and cherry-pick behind previews, backups, approval gates, and rollback tests.

### Phase 3 — forge adapters

Start with GitHub, then implement contract tests for GitLab, Bitbucket, Azure DevOps, Gitea, Forgejo, and generic remotes. Do not call an adapter connected until its minimum-permission round trip passes.

### Phase 4 — AI diagnostics

Connect the Coding and Diagnostic Engine. Provide AI suggestions, but require deterministic reproduction and verification for repairs.

### Phase 5 — portfolio product

Expose approved project health and build progress to aievolutionaryevolutions.com through a curated public feed.

## First executable slice

1. Define the canonical repository, commit, ref, change-request, pipeline, and receipt schemas.
2. Build a read-only adapter around local Git commands.
3. Generate a commit graph as JSON.
4. Test graph correctness against a synthetic repository.
5. Render the JSON in a minimal local interface.
6. Add no push, rebase, reset, deletion, or force operation in the first slice.
