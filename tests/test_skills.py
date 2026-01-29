"""
Tests for the skill factory.

Run with: pytest tests/ -v
"""
import pytest
from pydantic import BaseModel

from src.skills.base import BaseSkill, SkillResult, SkillErrorType
from src.skills.url_summarizer import UrlSummarizerInput, UrlSummarizerOutput


class TestSkillSchemas:
    """Test that skill schemas validate correctly."""
    
    def test_url_summarizer_input_valid(self):
        """Valid URL should pass validation."""
        input_data = {"url": "https://example.com/page"}
        validated = UrlSummarizerInput.model_validate(input_data)
        assert str(validated.url) == "https://example.com/page"
    
    def test_url_summarizer_input_invalid(self):
        """Invalid URL should fail validation."""
        input_data = {"url": "not-a-url"}
        with pytest.raises(Exception):
            UrlSummarizerInput.model_validate(input_data)
    
    def test_url_summarizer_output_valid(self):
        """Valid output should pass validation."""
        output_data = {
            "url": "https://example.com",
            "title": "Example Page",
            "summary": "This is an example page for testing.",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "content_type": "article",
            "word_count_estimate": 500,
            "language": "en"
        }
        validated = UrlSummarizerOutput.model_validate(output_data)
        assert validated.title == "Example Page"
        assert len(validated.key_points) == 3
    
    def test_url_summarizer_output_missing_field(self):
        """Missing required field should fail validation."""
        output_data = {
            "url": "https://example.com",
            "title": "Example Page",
            # missing other required fields
        }
        with pytest.raises(Exception):
            UrlSummarizerOutput.model_validate(output_data)


class TestSkillResult:
    """Test SkillResult dataclass."""
    
    def test_success_result(self):
        result = SkillResult(
            success=True,
            output={"key": "value"},
            tokens_used=100,
            latency_ms=500
        )
        assert result.success
        assert result.error_type is None
    
    def test_failure_result(self):
        result = SkillResult(
            success=False,
            output=None,
            error_type=SkillErrorType.VALIDATION_INPUT,
            error_message="Invalid input"
        )
        assert not result.success
        assert result.error_type == SkillErrorType.VALIDATION_INPUT
