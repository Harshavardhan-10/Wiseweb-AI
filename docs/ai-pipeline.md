# AI Pipeline

The AI layer (`app/ai/`) turns raw analyzer evidence into correlated,
actionable insight. It is **strictly evidence-bound**: the model is given
structured findings + evidence and must return output that conforms to
Pydantic schemas — invalid or non-JSON responses are rejected and retried
conservatively.

## Provider abstraction

`app/ai/provider.py` defines one interface:

```python
class AIProvider(ABC):
    async def complete(self, system: str, user: str) -> str: ...
    def available(self) -> bool: ...
```

Providers:

| Name | Backend | Notes |
| --- | --- | --- |
| `openai` | OpenAI-compatible `/chat/completions` | works with `AI_OPENAI_BASE_URL` for local/compatible endpoints |
| `anthropic` | Messages API | optional |
| `mock` | none (deterministic) | **default** — no API key needed |

If a configured provider lacks an API key, it logs a warning and falls back
to the mock provider. Selection: `AI_PROVIDER=openai|anthropic|mock`.

## Evidence grounding

Before any AI call, the orchestrator builds a context from **actual**
persisted data:

- findings (title, severity, confidence, affected_url),
- evidence items (type, source, value, metadata),
- detected technologies,
- score breakdown.

The mock provider is implemented as deterministic generators in
`recommendation_engine.py` + `analyzer.py`: it derives root causes and
recommendations from the real findings via rules (severity/impact/effort,
affected pages), and writes template summaries from the real score
breakdown. It never invents data.

## Output schemas (validated)

All AI output must parse into these Pydantic models (`app/ai/schemas.py`):

| Output | Schema | Content |
| --- | --- | --- |
| Root causes | `RootCauseOutput` | named root causes mapped to finding IDs |
| Recommendations | `RecommendationOutput` | title, description, category, impact, effort, confidence, root_cause, implementation_guidance, finding_ids |
| Summary | `SummaryOutput` | headline, executive_summary, top_risks, biggest_opportunities, roadmap |
| Change explanation | string | comparison summary between two scans |

Failures are handled defensively:

- non-JSON output → retry once → fall back to conservative defaults
- recommendation finding references are cross-checked against real findings
  (orphan references dropped; if none are referenced, the strongest finding
  in the category is linked)
- context is truncated to `AI_MAX_CONTEXT_CHARS` (24 000 by default)

## Pipeline stages (orchestrator)

1. `AI_CORRELATION` → `ai.root_causes(findings, evidence)`
2. `AI_RECOMMENDATIONS` → `ai.recommendations(findings, evidence, root_causes)` — output is then ranked by the deterministic priority engine (`scoring/priority.py`, see scoring.md) and persisted with P0–P3 buckets
3. `AI_SUMMARY` → `ai.summary(scores, findings, recommendations)` → `scan_summary` row

If a scan has zero findings, the AI phase is skipped entirely.

## Why deterministic prioritization?

Priorities and scores come from the **rule-based** engine, not the model.
AI provides the narrative (root causes, wording, roadmap) while numbers
remain explainable, reproducible, and testable. See docs/scoring.md for
formulas.
