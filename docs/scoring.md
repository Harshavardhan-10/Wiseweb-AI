# Scoring & Prioritization

All scores are computed by deterministic, rule-based engines
(`app/scoring/`) — the AI never sets numbers. This makes every score
reproducible and explainable.

## Health scores (100-point scale)

### Category score

Each category starts at **100** and deducts points per finding:

| Severity | Deduction |
| --- | --- |
| CRITICAL | 25.0 |
| HIGH | 15.0 |
| MEDIUM | 8.0 |
| LOW | 3.0 |
| INFO | 0.0 |

Each deduction is scaled by the finding's **confidence** (0–1):

```
score = 100 − Σ (deduction × confidence)
```

Clamped to `[0, 100]`, rounded to 1 decimal.

Example: one MEDIUM finding at 1.0 confidence → `100 − 8 = 92.0`.
A CRITICAL finding at 0.5 confidence → `100 − 12.5 = 87.5`.

### Unmeasured ≠ perfect

A category with **zero findings is recorded as `null` (unmeasured)**, not
100 — we can't claim health we never measured. The frontend renders this as
"Unmeasured".

### Overall score

Weighted average over measured categories only (unmeasured categories don't
dilute the average):

```
overall = Σ (category_score × weight) / Σ weights   (measured only)
```

Weights come from `app/scoring/industry_weights.py` keyed by website type
(portfolio, ecommerce, blog, saas, corporate, …) and default to uniform 1.0
for unknown types.

### Breakdown

Every computation returns a `breakdown` with per-category `score`,
`finding_count`, and `weight`, so the UI can explain any number.

## Recommendation priority (P0–P3)

`app/scoring/priority.py` ranks recommendations with an explicit formula:

```
priority_score =
    severity_weight × impact_weight × confidence × affected_page_factor × business_relevance
    ────────────────────────────────────────────────────────────────────────────────────────
                                        effort_weight
```

| Factor | Scale | Source |
| --- | --- | --- |
| severity_weight | CRITICAL 4 · HIGH 3 · MEDIUM 2 · LOW 1 · INFO 0 | finding severity |
| impact_weight | CRITICAL 4 · HIGH 3 · MEDIUM 2 · LOW 1 | AI assessment |
| confidence | 0–1 (clamped) | AI + evidence confidence |
| affected_page_factor | `1 + 0.5 × min(affected/total, 1)` | how much of the site is hit |
| business_relevance | 1.0 (uniform for now) | future: industry weighting |
| effort_weight | HIGH 3 · MEDIUM 2 · LOW 1 | AI assessment (in the denominator — cheaper fixes rank higher) |

### Buckets with hard ceilings

| Bucket | Score range |
| --- | --- |
| P0 | ≥ 24.0 |
| P1 | ≥ 12.0 |
| P2 | ≥ 5.0 |
| P3 | < 5.0 |

The ceilings prevent any single factor from skewing rankings — e.g. a
CRITICAL/HIGH pair without a wide reach lands at P1, not P0.

Worked example: severity CRITICAL (4) × impact CRITICAL (4) × confidence 1.0
× affected_factor 1.5 ÷ effort LOW (1) = **24.0 → P0**.
The same with MEDIUM impact and HIGH effort: 4 × 2 × 1.0 × 1.5 / 3 = 4.0 → P3.

Every recommendation stores `priority_score` and a
`priority_explanation` string describing the factors used.

## Related modules

- `app/scoring/severity.py` — point tables shared by both engines.
- `app/scoring/health_score.py` — category + overall computation.
- `app/scoring/priority.py` — recommendation ranking.
- Tests: `backend/tests/unit/test_scoring.py`, `test_priority.py`.
