"""Potential content similarity detection (within the crawled site).

Uses character n-gram shingles and Jaccard similarity. The output is
deliberately conservative:

  - "Potential content similarity"
  - "Requires human review."

No legal conclusions are ever drawn here.
"""

import re
from collections import Counter

from app.analyzers.base import EvidenceDraft, FindingDraft

SHINGLE_SIZE = 6  # character n-grams
SIMILARITY_THRESHOLD = 0.55
MAX_SHINGLES = 400

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def _shingles(text: str) -> Counter[str]:
    words = _TOKEN_RE.findall(text.lower())
    if len(words) < 20:
        return Counter()
    seq = " ".join(words)
    count = Counter()
    for i in range(len(words) - SHINGLE_SIZE + 1):
        shingle = " ".join(words[i : i + SHINGLE_SIZE])
        count[shingle] += 1
    return count


def _jaccard(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 0.0


def detect_page_similarity(pages) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    bodies = [(p, _shingles(p.text)) for p in pages if p.text]
    if len(bodies) < 2:
        return findings

    compared = 0
    for i, (page_a, sig_a) in enumerate(bodies):
        for page_b, sig_b in bodies[i + 1 :]:
            score = _jaccard(sig_a, sig_b)
            compared += 1
            if score >= SIMILARITY_THRESHOLD:
                findings.append(
                    FindingDraft(
                        rule_id="CONTENT_POTENTIAL_SIMILARITY",
                        title="Potential content similarity between two pages",
                        severity="LOW",
                        confidence=round(score, 2),
                        impact="LOW",
                        effort="MEDIUM",
                        description=(
                            f"'{page_a.url}' and '{page_b.url}' share a high "
                            f"similarity score ({score:.0%}) computed over text "
                            "n-grams. This is a potential signal only — requires "
                            "human review before any conclusion."
                        ),
                        affected_url=page_a.url,
                        evidence=[
                            EvidenceDraft(
                                "METRIC", page_a.url,
                                f"similarity_score={score:.2f} vs {page_b.url}",
                                metadata={"similarity_score": round(score, 3)},
                            )
                        ],
                    )
                )
                if len(findings) >= 5:
                    return findings
            if compared >= 60:
                return findings
    return findings
