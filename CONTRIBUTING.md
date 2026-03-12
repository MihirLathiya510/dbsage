# Contributing

Contributions are welcome — tools, bug fixes, documentation, and database driver support.

## Quick start

1. Fork the repo on GitHub
2. Clone your fork and set up:

```bash
git clone https://github.com/your-username/dbsage.git
cd dbsage
git remote add upstream https://github.com/MihirLathiya510/dbsage.git
uv sync --extra dev
uv run pytest       # should all pass
```

No database required. All tests mock the DB layer.

## What we're looking for

- New MCP tools that help LLMs explore and query databases more effectively
- Improvements to the safety guardrails (query validator, rewriter)
- PostgreSQL-specific fixes (most development has been on MySQL)
- Better output formatting for edge cases
- Documentation improvements

## Project values

**Safety first.** The read-only guarantee is non-negotiable. Any change that could allow data modification — even indirectly — will not be merged. When in doubt, block more, not less.

**LLM-readable output.** Tools return plain text, not JSON. Structure matters: consistent headers, aligned columns, timing footers. If you change output format, think about whether an LLM can still parse it reliably.

**No unnecessary dependencies.** Every dependency increases uvx install time and the attack surface. Open an issue to discuss before adding anything.

## Detailed guide

Architecture, how to add a tool, testing conventions, and the full PR checklist: [docs/contributing.md](docs/contributing.md)

## Issues and discussions

- Bug reports: open an issue with the tool name, input, and actual vs expected output
- New tool ideas: open an issue before writing code — let's discuss whether it fits the scope
- Questions: open a discussion
