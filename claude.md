# Tonari

## Project Structure

The project uses:
- **Frontend:** React with TypeScript, Chakra UI v3
- **Backend:** Python FastAPI with Alembic migrations
- **Docker:** Docker Compose for local development
- **Package Manager:** npm (frontend), pip (backend)

## Development Commands

This project uses `just` as a task runner. See `justfile` for all available commands:

**Common commands:**
- `just dev-up` - Start development environment (db, api-dev, and frontend)
- `just dev-down` - Stop development environment
- `just test` - Run backend tests
- `just lint` - Lint backend code
- `just format` - Format backend code
- `just lint-web` - Lint frontend code with Biome
- `just format-web` - Format frontend code with Biome
- `just migrate` - Run database migrations
- `just makemigrations [name]` - Generate new migration
- `just generate-api` - Generate frontend API client from OpenAPI spec
- `just --list` - See all available just recipes

## Long-Running Task Tracking

Multi-session tasks live under `.ai/active/`. Each subdirectory is a self-contained task with this layout:

```
.ai/active/<task>/
├── state.md              # compact current state; overwritten each session
├── log.md                # append-only session history
├── <design-doc>.md       # PRDs, plans, mockups at top level (as many as needed)
├── phase-1/              # one folder per phase (typically one PR per phase)
│   └── review.md         # shared review doc; reviewers append sections
├── phase-2/
└── ...
```

- **`state.md`** — status, phase summary table, next steps, blockers. Overwritten each session. Read this first when resuming.
- **`log.md`** — append-only session history. Consult only when you need past decisions.
- **Top-level docs** — PRD, plan, mockups, and other design artifacts that span the whole task.
- **`phase-<n>/`** — one folder per phase (roughly one PR). Phase-scoped artifacts live here.
- **`phase-<n>/review.md`** — shared, append-only review document. Multiple reviewers (possibly different models) add sections to the same file so a human can read one consolidated review.

When starting a session: read `state.md`. When ending: overwrite `state.md`, append to `log.md`.

### review.md format

Each reviewer appends a block of this form — never edit or remove prior blocks:

```markdown
## Review — <your model id> — <YYYY-MM-DD>

**Files reviewed**: comma-separated list
**Changes**: brief one-line description

### Critical
- **[file:line]** Description → Suggested fix

### Important
- **[file:line]** Description → Suggested fix

### Minor
- **[file:line]** Description

### Summary
One sentence: overall assessment and whether this is safe to commit.

---
```

Omit empty severity sections. If the file doesn't exist yet, create it with a `# Phase <n> Review` heading, then add your block.

## Available MCPs (Model Context Protocols)

### Codanna
Codanna is a code intelligence MCP for analyzing and searching the codebase.

**Use Codanna for:**
- Finding and understanding code symbols (functions, classes, types, etc.)
- Analyzing code relationships and dependencies
- Understanding function calls and call chains
- Searching for specific code patterns
- Analyzing impact of code changes

**Refer to claude.md for detailed Codanna documentation and workflows.**

### Chakra UI
Chakra UI MCP for building and designing UI components.

**Use Chakra UI for:**
- Building accessible React components
- Designing UI layouts and components
- Getting component examples and patterns
- Customizing themes and design tokens
- Understanding Chakra UI API and component props

**Available Chakra UI Tools:**
- `mcp__chakra-ui__get_theme` - Retrieve the theme specification
- `mcp__chakra-ui__list_components` - List all available Chakra UI components
- `mcp__chakra-ui__get_component_props` - Get properties for a specific component
- `mcp__chakra-ui__get_component_example` - Get example code for a component
- `mcp__chakra-ui__customize_theme` - Setup custom theme tokens
- `mcp__chakra-ui__installation` - Get installation steps
- `mcp__chakra-ui__v2_to_v3_code_review` - Get migration guidance for v2 to v3

**Best Practices:** Always review generated code with `v2_to_v3_code_review` to avoid hallucination and ensure compatibility.
