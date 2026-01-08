"""Rubric configuration database models."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from api.db.database import Base

if TYPE_CHECKING:
    from api.auth.models import User


class UserRubricConfig(Base):
    """User's custom rubric configuration."""

    __tablename__ = "user_rubric_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Default", "Strict", "Lenient"
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Global settings
    min_description_words = Column(Integer, default=20)
    require_acceptance_criteria = Column(Boolean, default=True)
    allowed_labels = Column(JSON, nullable=True)  # List of allowed labels

    # Relationships
    user = relationship("User", back_populates="rubric_configs")
    rules = relationship("RubricRule", back_populates="config", cascade="all, delete-orphan")
    ambiguous_terms = relationship("AmbiguousTerm", back_populates="config", cascade="all, delete-orphan")


class RubricRule(Base):
    """Individual rubric rule with weight and thresholds."""

    __tablename__ = "rubric_rules"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("user_rubric_configs.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(String(50), nullable=False)  # e.g., "title_clarity", "description_length"
    weight = Column(Float, default=1.0)
    is_enabled = Column(Boolean, default=True)

    # Rule-specific thresholds (JSON for flexibility)
    thresholds = Column(JSON, nullable=True)
    # Example: {"min_title_length": 10, "max_title_length": 100}

    # Relationships
    config = relationship("UserRubricConfig", back_populates="rules")


class AmbiguousTerm(Base):
    """User-customizable ambiguous terms."""

    __tablename__ = "ambiguous_terms"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("user_rubric_configs.id", ondelete="CASCADE"), nullable=False)
    term = Column(String(100), nullable=False)

    # Relationships
    config = relationship("UserRubricConfig", back_populates="ambiguous_terms")


# Default rubric rules configuration
DEFAULT_RUBRIC_RULES = [
    {
        "rule_id": "title_clarity",
        "name": "Title Clarity",
        "description": "Check if title is clear, actionable, and appropriately sized",
        "weight": 1.0,
        "thresholds": {
            "min_length": 10,
            "max_length": 100,
            "filler_words": ["just", "maybe", "perhaps", "kinda", "sort of"],
            "action_words": ["add", "fix", "create", "update", "remove", "implement", "refactor"],
        },
    },
    {
        "rule_id": "description_length",
        "name": "Description Length",
        "description": "Check if description meets minimum word count",
        "weight": 1.2,
        "thresholds": {
            "min_words": 20,
        },
    },
    {
        "rule_id": "acceptance_criteria",
        "name": "Acceptance Criteria",
        "description": "Check for presence of testable acceptance criteria",
        "weight": 1.5,
        "thresholds": {
            "patterns": [
                "acceptance criteria",
                "ac:",
                "given.*when.*then",
                "requirements:",
                "must:",
            ],
        },
    },
    {
        "rule_id": "ambiguous_terms",
        "name": "Ambiguous Terms",
        "description": "Check for vague or ambiguous language",
        "weight": 1.0,
        "thresholds": {
            "penalty_per_term": 0.15,
        },
    },
    {
        "rule_id": "estimate_present",
        "name": "Estimate Present",
        "description": "Check if story points or time estimate is provided",
        "weight": 0.8,
        "thresholds": {},
    },
    {
        "rule_id": "labels",
        "name": "Labels",
        "description": "Check for appropriate labeling",
        "weight": 0.7,
        "thresholds": {},
    },
    {
        "rule_id": "scope_clarity",
        "name": "Scope Clarity",
        "description": "Check if scope is clearly defined with boundaries",
        "weight": 1.0,
        "thresholds": {
            "scope_indicators": [
                "out of scope",
                "in scope",
                "dependencies:",
                "blocked by",
                "requires",
                "affects",
            ],
            "broad_words": ["everything", "all", "any", "complete", "total", "entire"],
        },
    },
]

DEFAULT_AMBIGUOUS_TERMS = [
    "optimize",
    "ASAP",
    "soon",
    "quickly",
    "improve",
    "better",
    "enhance",
    "fix",
    "update",
]
