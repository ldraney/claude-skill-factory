"""
Base Skill Definition

Every skill in the factory follows this interface.
Skills are testable, schema-validated units of AI work.
"""
from abc import ABC, abstractmethod
from pydantic import BaseModel, ValidationError
from typing import Type, Any
from dataclasses import dataclass
from enum import Enum


class SkillErrorType(str, Enum):
    """Categorized errors for observability."""
    VALIDATION_INPUT = "validation_input"      # Bad input data
    VALIDATION_OUTPUT = "validation_output"    # LLM returned invalid schema
    API_ERROR = "api_error"                    # Anthropic API failure
    RATE_LIMIT = "rate_limit"                  # Hit rate limits
    TIMEOUT = "timeout"                        # Took too long
    CONFIDENCE_LOW = "confidence_low"          # LLM unsure
    SOURCE_NOT_FOUND = "source_not_found"      # Referenced data missing


@dataclass
class SkillResult:
    """Result of running a skill on one input."""
    success: bool
    output: dict | None
    error_type: SkillErrorType | None = None
    error_message: str | None = None
    tokens_used: int = 0
    latency_ms: int = 0


class BaseSkill(ABC):
    """
    Abstract base for all skills.
    
    To create a new skill:
    1. Define input_schema (Pydantic model)
    2. Define output_schema (Pydantic model)  
    3. Implement execute()
    """
    
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    
    # Optional: tools this skill can use
    tools: list[dict] = []
    
    # Optional: system prompt override
    system_prompt: str | None = None
    
    def validate_input(self, data: dict) -> tuple[bool, Any]:
        """Validate input against schema. Returns (is_valid, validated_or_error)."""
        try:
            validated = self.input_schema.model_validate(data)
            return True, validated
        except ValidationError as e:
            return False, str(e)
    
    def validate_output(self, data: dict) -> tuple[bool, Any]:
        """Validate output against schema. Returns (is_valid, validated_or_error)."""
        try:
            validated = self.output_schema.model_validate(data)
            return True, validated
        except ValidationError as e:
            return False, str(e)
    
    @abstractmethod
    async def execute(self, validated_input: BaseModel) -> SkillResult:
        """
        Execute the skill on validated input.
        
        This is where the Claude API call happens.
        Must return a SkillResult with structured output or error.
        """
        pass
    
    async def run(self, raw_input: dict) -> SkillResult:
        """
        Full pipeline: validate input → execute → validate output.
        
        This is what the queue worker calls.
        """
        import time
        start = time.time()
        
        # Validate input
        is_valid, result = self.validate_input(raw_input)
        if not is_valid:
            return SkillResult(
                success=False,
                output=None,
                error_type=SkillErrorType.VALIDATION_INPUT,
                error_message=result
            )
        
        # Execute skill
        skill_result = await self.execute(result)
        skill_result.latency_ms = int((time.time() - start) * 1000)
        
        # If execution succeeded, validate output
        if skill_result.success and skill_result.output:
            is_valid, validated = self.validate_output(skill_result.output)
            if not is_valid:
                return SkillResult(
                    success=False,
                    output=skill_result.output,  # Include raw for debugging
                    error_type=SkillErrorType.VALIDATION_OUTPUT,
                    error_message=validated,
                    tokens_used=skill_result.tokens_used,
                    latency_ms=skill_result.latency_ms
                )
        
        return skill_result
