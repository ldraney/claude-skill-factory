"""
Skill Registry

Central registry of all available skills.
New skills are added here to be discoverable by the API.
"""
from src.skills.base import BaseSkill
from src.skills.url_summarizer import url_summarizer


# Registry: skill_name -> skill instance
SKILL_REGISTRY: dict[str, BaseSkill] = {
    "url_summarizer": url_summarizer,
}


def get_skill(name: str) -> BaseSkill | None:
    """Get a skill by name."""
    return SKILL_REGISTRY.get(name)


def register_skill(skill: BaseSkill) -> None:
    """Register a new skill."""
    SKILL_REGISTRY[skill.name] = skill


def list_skills() -> list[str]:
    """List all registered skill names."""
    return list(SKILL_REGISTRY.keys())
