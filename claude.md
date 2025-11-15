# Claude Code Configuration for Tonari

This file documents the Claude Code setup and available tools for this project.

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

## Project Structure

The project uses:
- **Frontend:** React with TypeScript, Chakra UI v3
- **Backend:** Python FastAPI with Alembic migrations
- **Docker:** Docker Compose for local development
- **Package Manager:** npm (frontend), pip (backend)

## Development Commands

This project uses `just` as a task runner. See `justfile` for all available commands:

**Common commands:**
- `just dev-up` - Start development environment (db and api-dev)
- `just dev-down` - Stop development environment
- `just test` - Run backend tests
- `just lint` - Lint backend code
- `just format` - Format backend code
- `just lint-web` - Lint frontend code with Biome
- `just migrate` - Run database migrations
- `just makemigrations [name]` - Generate new migration
- `just generate-api` - Generate frontend API client from OpenAPI spec
- `just --list` - See all available just recipes
