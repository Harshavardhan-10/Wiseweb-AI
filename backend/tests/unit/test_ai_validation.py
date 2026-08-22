"""AI output validation tests: garbage input must be rejected so the
pipeline never persists unvalidated model output."""

import pytest
from pydantic import ValidationError as PydanticError

from app.ai.schemas import CompetitorOutput, RecommendationOutput, RootCauseOutput


def test_root_cause_output_valid():
    parsed = RootCauseOutput.model_validate_json(
        '{"root_causes": [{"title": "Slow TTFB", "confidence": 0.8, '
        '"affected_findings": ["PERF_TTFB_01"]}]}'
    )
    assert parsed.root_causes[0].title == "Slow TTFB"


def test_root_cause_output_rejects_confidence_out_of_range():
    with pytest.raises(PydanticError):
        RootCauseOutput.model_validate_json(
            '{"root_causes": [{"title": "x", "confidence": 1.7}]}'
        )


def test_recommendation_output_defaults():
    parsed = RecommendationOutput.model_validate_json('{"recommendations": [{"title": "x"}]}')
    rec = parsed.recommendations[0]
    assert rec.priority == "P2" and rec.impact == "MEDIUM" and rec.confidence == 0.5


def test_recommendation_output_rejects_missing_title():
    with pytest.raises(PydanticError):
        RecommendationOutput.model_validate_json('{"recommendations": [{}]}')


def test_competitor_output_rejects_missing_dimension():
    with pytest.raises(PydanticError):
        CompetitorOutput.model_validate_json(
            '{"gaps": [{"you": 5, "competitor": 3}]}'
        )


def test_rejects_non_json():
    with pytest.raises(PydanticError):
        RecommendationOutput.model_validate_json("not json at all")
