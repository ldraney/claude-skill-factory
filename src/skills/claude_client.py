"""
Claude API Client

Handles structured output extraction from Claude.
Uses JSON mode + Pydantic validation (not instructor, to keep deps minimal).
"""
import os
import json
import anthropic
from pydantic import BaseModel
from typing import Type

from src.skills.base import SkillResult, SkillErrorType


# Initialize client (uses ANTHROPIC_API_KEY env var)
def get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic()


async def call_claude_structured(
    prompt: str,
    output_schema: Type[BaseModel],
    system_prompt: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    temperature: float = 0.0
) -> SkillResult:
    """
    Call Claude and parse response into a Pydantic model.
    
    Uses low temperature for consistency.
    Validates output against schema.
    """
    client = get_client()
    
    # Build messages
    messages = [{"role": "user", "content": prompt}]
    
    # Add JSON instruction to system prompt
    json_instruction = f"""

IMPORTANT: Respond with ONLY valid JSON. No markdown, no explanation, no code blocks.
The JSON must match this schema:
{json.dumps(output_schema.model_json_schema(), indent=2)}"""
    
    full_system = (system_prompt or "") + json_instruction
    
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=full_system,
            messages=messages
        )
        
        # Extract text content
        raw_text = response.content[0].text.strip()
        
        # Try to parse JSON (handle markdown code blocks if model ignores instruction)
        if raw_text.startswith("```"):
            # Strip markdown code block
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1])
        
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as e:
            return SkillResult(
                success=False,
                output={"raw_response": raw_text},
                error_type=SkillErrorType.VALIDATION_OUTPUT,
                error_message=f"Invalid JSON from Claude: {str(e)}",
                tokens_used=response.usage.input_tokens + response.usage.output_tokens
            )
        
        # Validate against schema
        try:
            validated = output_schema.model_validate(parsed)
            return SkillResult(
                success=True,
                output=validated.model_dump(),
                tokens_used=response.usage.input_tokens + response.usage.output_tokens
            )
        except Exception as e:
            return SkillResult(
                success=False,
                output=parsed,
                error_type=SkillErrorType.VALIDATION_OUTPUT,
                error_message=f"Schema validation failed: {str(e)}",
                tokens_used=response.usage.input_tokens + response.usage.output_tokens
            )
            
    except anthropic.RateLimitError as e:
        return SkillResult(
            success=False,
            output=None,
            error_type=SkillErrorType.RATE_LIMIT,
            error_message=str(e)
        )
    except anthropic.APIError as e:
        return SkillResult(
            success=False,
            output=None,
            error_type=SkillErrorType.API_ERROR,
            error_message=str(e)
        )
