# Codebase Review Process

## Goal

Run a codebase-wide review in parallel without losing systemwide context, severity consistency, or ownership clarity.

## Operating Model

The review uses a hub-and-spoke model:

- the main agent owns review strategy, system context, prioritization, and final synthesis
- subagents perform bounded analysis on specific subsystems
- canonical review artifacts are maintained by the main agent

This keeps the overall review coherent while still allowing parallel deep dives.

## Canonical Files

The main agent owns updates to:

- `plan.md`
- `progress.md`
- `findings.md`
- `checklist.md`
- `process.md`

Subagents should not write directly to these files unless explicitly instructed.

## Main Agent Responsibilities

The main agent is responsible for:

- defining review phases and subsystem order
- running and recording baseline checks
- maintaining the system map and global risk picture
- deciding what work can run in parallel
- assigning subagent scopes
- deduplicating findings
- normalizing severity
- writing the final findings and remediation backlog

## Subagent Responsibilities

Subagents are responsible for:

- reviewing only their assigned scope
- collecting evidence-backed findings
- identifying likely regressions and test gaps
- returning structured notes to the main agent

Subagents should not:

- redefine severity rules
- make final prioritization decisions outside their scope
- duplicate broad repo-wide exploration already done by the main agent
- overwrite or reorganize canonical review artifacts

## Review Workflow

### Phase 1: Main Agent Baseline

The main agent first:

- runs tests, lint, and build checks
- inspects repo structure and entry points
- identifies high-risk flows
- updates `progress.md` and `checklist.md`

No subagents should be spawned until this baseline exists.

### Phase 2: Parallel Subsystem Review

Once the baseline is established, the main agent can split work into bounded review lanes.

Recommended lanes for this repo:

- backend workflows: routers, services, agents, and write paths
- data model and migrations: SQLAlchemy models, constraints, Alembic history
- frontend workflows: pages, hooks, API usage, state management
- tests and tooling: automated coverage, missing regressions, build/lint health

### Phase 3: Consolidation

The main agent:

- reviews each subagent output
- merges duplicates
- checks for cross-subsystem interactions
- translates raw observations into formal findings
- updates `findings.md`, `progress.md`, and `checklist.md`

### Phase 4: Systemwide Pass

After subsystem reviews, the main agent performs a final cross-cutting pass for:

- contract drift between backend and frontend
- error handling consistency
- configuration and environment assumptions
- logging and observability gaps
- systemic test debt

## Task Breakdown Rules

Subagent tasks should be:

- narrow enough to finish independently
- broad enough to surface meaningful risks
- assigned by subsystem or flow, not random files
- non-overlapping where possible

Good task examples:

- review translation creation, persistence, and explanation flows
- review prompt, prompt version, and snapshot behavior
- review work detail and chapter detail frontend flows
- review DB constraints and migration/model alignment

Bad task examples:

- review the backend
- review everything about prompts and frontend and tests
- read files and report anything suspicious

## Context Preservation Rules

To preserve systemwide context:

1. The main agent defines the rubric before parallel work begins.
2. The main agent provides each subagent with repo context and scope boundaries.
3. The main agent keeps the canonical hotspot map and severity model.
4. The main agent is the only source of final finding IDs and statuses.
5. Subagent outputs are treated as inputs to synthesis, not final review artifacts.

## Subagent Output Format

Each subagent should return findings in a structured format like:

```text
Scope:
- backend translation flow

Findings:
1. Title
   Severity suggestion: P1
   Files: path1, path2
   Summary: concise statement of the issue
   Risk: why this matters
   Confidence: high/medium/low
   Suggested action: likely remediation direction
   Test follow-up: specific missing or needed test

Open questions:
- anything that needs confirmation from the main agent
```

The main agent can then normalize this into `findings.md`.

## Scratch Work

If subagents need persistent notes, use scratch files under:

- `.ai/active/codebase-review/agents/`

Suggested files:

- `agents/backend.md`
- `agents/data-model.md`
- `agents/frontend.md`
- `agents/tests-tooling.md`

These are working notes only. They are not canonical findings.

## Severity Ownership

Subagents may suggest severity, but final severity is assigned by the main agent.

Severity should consider:

- user impact
- data integrity risk
- operational or cost impact
- likelihood of regression
- breadth of affected workflows

## Conflict Resolution

If two subagents report overlapping issues:

- the main agent merges them into a single finding where appropriate
- subsystem-specific details can remain in scratch notes
- the final finding should describe the system-level problem once

If a subagent finds an issue outside its assigned scope:

- it should note it briefly
- it should avoid expanding the review boundary unless instructed

## Completion Criteria

A subsystem pass is complete when:

- critical flows in scope were inspected
- concrete findings or an explicit no-finding result were returned
- major test gaps were identified
- any open questions were called out

The codebase review is complete when:

- all checklist sections have been reviewed
- findings are recorded and prioritized
- major hotspots are summarized
- a remediation backlog exists

