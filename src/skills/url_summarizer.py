"""
URL Summarizer Skill

The first skill: fetch a URL and produce a structured summary.
This proves the full pipeline works.
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
import httpx

from src.skills.base import BaseSkill, SkillResult, SkillErrorType
from src.skills.claude_client import call_claude_structured


class UrlSummarizerInput(BaseModel):
    """Input schema: just a URL."""
    url: HttpUrl = Field(description="The URL to fetch and summarize")


class UrlSummarizerOutput(BaseModel):
    """Output schema: structured summary data."""
    url: str = Field(description="The original URL")
    title: str = Field(description="Page title or inferred title")
    summary: str = Field(description="2-3 sentence summary of main content")
    key_points: list[str] = Field(description="3-5 key points from the content", max_length=5)
    content_type: str = Field(description="Type: article, product, documentation, blog, other")
    word_count_estimate: int = Field(description="Estimated word count of main content")
    language: str = Field(description="Detected language code (en, es, etc)")


class UrlSummarizerSkill(BaseSkill):
    """
    Skill: Given a URL, fetch it and produce a structured summary.
    
    This is the "hello world" of the skill factory.
    """
    
    name = "url_summarizer"
    description = "Fetch a URL and produce a structured summary with key points"
    input_schema = UrlSummarizerInput
    output_schema = UrlSummarizerOutput
    
    system_prompt = """You are a content analyzer. Given webpage content, extract structured information.

Be factual and concise. If content is unclear or missing, make reasonable inferences but note uncertainty.

Always respond with valid JSON matching the exact schema requested."""

    async def execute(self, validated_input: UrlSummarizerInput) -> SkillResult:
        """Fetch URL content and summarize with Claude."""
        
        url = str(validated_input.url)
        
        # Step 1: Fetch the URL
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                content = response.text[:50000]  # Limit content size
        except httpx.TimeoutException:
            return SkillResult(
                success=False,
                output=None,
                error_type=SkillErrorType.TIMEOUT,
                error_message=f"Timeout fetching URL: {url}"
            )
        except httpx.HTTPError as e:
            return SkillResult(
                success=False,
                output=None,
                error_type=SkillErrorType.SOURCE_NOT_FOUND,
                error_message=f"HTTP error fetching URL: {str(e)}"
            )
        
        # Step 2: Call Claude for structured summary
        prompt = f"""Analyze this webpage content and provide a structured summary.

URL: {url}

CONTENT:
{content}

Respond with JSON matching this exact structure:
- url: the original URL
- title: page title or inferred title
- summary: 2-3 sentence summary
- key_points: array of 3-5 key points
- content_type: one of (article, product, documentation, blog, other)
- word_count_estimate: estimated word count
- language: language code (en, es, etc)"""

        result = await call_claude_structured(
            prompt=prompt,
            output_schema=UrlSummarizerOutput,
            system_prompt=self.system_prompt
        )
        
        return result


# Singleton instance for registry
url_summarizer = UrlSummarizerSkill()
