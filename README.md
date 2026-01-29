# Claude Skill Factory

Industrial-grade pipeline for processing data through Claude skills at scale.

## Philosophy

> "AI can autocomplete but can't comprehend; therefore TDD + observability based on user story is fastest development philosophy."

This isn't a chatbot. It's a **data processing factory** that happens to use LLMs.

## The Loop

```
Input (batch) → Queue → Skill (Claude + Tools) → Validate → Output (structured)
```

Every skill:
- Has a defined input schema
- Has a defined output schema (Pydantic)
- Is testable in isolation
- Fails loudly with categorized errors

## Quick Start

```bash
docker-compose up -d          # Redis + Postgres
cp .env.example .env          # Add your ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

## First User Story

> "As an operator, I submit a CSV of 100 URLs. The system queues them, runs a 'summarize' skill on each, and writes structured JSON summaries to a database table I can query."

See [docs/user-stories.html](docs/user-stories.html) for full backlog.

## Architecture

See [docs/architecture.html](docs/architecture.html)

## Project Status

🚧 **Building in public** — [Roadmap](docs/roadmap.html)

## License

MIT
