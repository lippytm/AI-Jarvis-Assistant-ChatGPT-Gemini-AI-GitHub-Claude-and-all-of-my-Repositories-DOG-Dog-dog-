# Jarvis automation plan

## 1. Automate — highest time savings

**Code and issue review.** On repository changes, Jarvis reads the diff, tests, and linked issues, then posts a review summary or opens a draft issue. Use GitHub Actions plus the provider adapters defined in `.jarvis/config.yaml`.

## 2. Automate

**Shared knowledge synchronization.** Changes to versioned instructions and documents trigger an idempotent index refresh. Conflicts stop the run and create a review issue.

## 3. Automate

**Test and deployment preparation.** Every pull request runs validation and produces a deployment readiness report. Production deployment remains approval-gated.

## 4. Template

**Issue and pull-request briefs.** Use a standard brief containing objective, context, affected repositories, acceptance criteria, risks, tests, and rollback plan.

## 5. Template

**Documentation drafts.** Use the same structure for README updates, technical guides, affiliate-marketing workflows, and business-financing process documentation: purpose, audience, prerequisites, workflow, controls, examples, and next actions.

## 6. Eliminate

**Duplicate provider-specific instruction copies.** Keep canonical instructions in GitHub and generate provider prompts from them. Independent copies drift and create contradictory Jarvis behavior.

## 7. Eliminate

**Manual “is it ready?” checks.** Replace them with the workflow readiness report and approval record.

## Guardrails

Do not automate external messages, production deployments, merges, destructive changes, financial commitments, or secret handling without explicit approval.
