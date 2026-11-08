# AI Jarvis Governed Build Order

## Objective
Unify the AI Jarvis assistants, swarms, communications network, GitHub repositories, Hostinger services, education products, and affiliate-business workflows while keeping production changes approval-gated.

## Verified starting point
- KVM 8 is running Arch Linux.
- Jarvis services are listening on ports 3002 and 3003.
- Docker is not installed on KVM 8, so Docker and Traefik workloads must not be assumed to exist there.
- No failed systemd units were reported during the read-only check.
- GitHub is connected and the primary Jarvis repository contains task templates and a problem-council workflow.
- The public Cloud Professional hosting resource is active on the .online domain.
- The .com domain is active, but the website resource previously attached to it is suspended and cannot be edited until restored.

## Build order

### 1. Governance and safety baseline
- Define one source of truth for projects, services, owners, secrets, environments, and release status.
- Require read-only discovery by default.
- Require explicit approval for production changes, credential changes, deployments, billing changes, destructive actions, and public publishing.
- Record provenance for every AI output, including model, timestamp, source repository, confidence, reviewer, and final disposition.

### 2. KVM 8 runtime foundation
- Keep KVM 8 as the protected Jarvis backend.
- Document the current Node services on ports 3002 and 3003.
- Do not install or migrate Docker/Traefik without a separate operating-system and rollback decision.
- Add health checks, logs, backup checks, firewall review, secret handling, and recovery documentation before adding more services.

### 3. GitHub portfolio control plane
- Inventory repositories for the primary and secondary GitHub accounts.
- Group repositories into core runtime, agents, workflows, education, websites, experiments, and archived candidates.
- Review branches, workflows, dependency manifests, secrets references, documentation, tests, and deployment paths.
- Produce read-only QA, security, architecture, documentation, workflow, and Prompt #11 compliance findings.
- Do not modify code automatically. Changes require a reviewable patch and approval.

### 4. AI model normalization layer
- Normalize ChatGPT/OpenAI, ChatGPT Business, Gemini, Claude, Perplexity, and local-model inputs.
- Preserve source and attachment provenance.
- Convert approved outputs into tasks, tests, documentation, and swarm assignments.
- Add conflict detection, human review, redaction checks, and duplicate suppression.
- Treat ChatGPT Business as an external connection or API input only after its exact supported connection method is identified.

### 5. Jarvis swarm and communications layer
- Define roles for intake, planner, researcher, coder, QA, security, documentation, finance, marketing, and release management.
- Use a coordinator to route work and prevent duplicate execution.
- Add retry limits, timeouts, escalation states, audit events, and rollback references.
- Keep external communications and public publishing approval-gated.

### 6. Education and revenue layer
- Launch the AI/Linux/programming/blockchain learning membership first.
- Add a controlled AI systems builder retainer after the first learning path is validated.
- Add business automation care plans and the affiliate resource club after repeat demand is measured.
- Track subscriptions, trials, churn, recurring revenue, customer outcomes, and affiliate commissions separately.
- Label and disclose every affiliate relationship. Never present an affiliate link as an independent recommendation.

### 7. Website and affiliate layer
- Use the active .online hosting resource for public education and affiliate content until the .com website is restored.
- Treat Hostinger Referral, any separate Hostinger Affiliate enrollment, CLONECAST, and other programs as separate programs with separate terms, links, and tracking IDs.
- Do not invent or reuse a tracking link between programs.
- Add tagged links, disclosure text, click events, conversion events, and an audit log only after each verified link is available.

### 8. Release gates
A release is ready only when:
- backups and rollback are verified;
- secrets are protected and least-privilege;
- tests and health checks pass;
- security and dependency findings are reviewed;
- documentation is updated;
- affiliate disclosures are present where applicable;
- production, billing, and public-publishing changes have explicit approval.

## Immediate blockers
1. The .com website must be restored before it can be edited.
2. A usable Hostinger referral or affiliate URL must be retrieved before tracking can be added.
3. The exact supported connection method for ChatGPT Business must be identified.
4. KVM 8's Arch runtime must be kept consistent with the current Node-based services unless an approved OS/runtime migration is planned.

## Immediate next safe actions
- Complete a read-only repository inventory and QA/security pass.
- Create the canonical project and service registry.
- Verify backups and health checks for KVM 8.
- Restore the .com site only through an approved billing action.
- Add affiliate tracking only after links and disclosures are verified.
