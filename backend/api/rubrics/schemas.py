"""Rubric configuration Pydantic schemas."""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class RubricRuleResponse(BaseModel):
    """Schema for a rubric rule."""

    id: int
    rule_id: str
    name: str
    description: str
    weight: float
    is_enabled: bool
    thresholds: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class RubricRuleUpdate(BaseModel):
    """Schema for updating a rubric rule."""

    weight: Optional[float] = Field(None, ge=0, le=5)
    is_enabled: Optional[bool] = None
    thresholds: Optional[dict[str, Any]] = None


class RubricConfigCreate(BaseModel):
    """Schema for creating a rubric configuration."""

    name: str = Field(..., max_length=100)
    min_description_words: int = Field(default=20, ge=5, le=500)
    require_acceptance_criteria: bool = True
    allowed_labels: Optional[list[str]] = None


class RubricConfigUpdate(BaseModel):
    """Schema for updating a rubric configuration."""

    name: Optional[str] = Field(None, max_length=100)
    min_description_words: Optional[int] = Field(None, ge=5, le=500)
    require_acceptance_criteria: Optional[bool] = None
    allowed_labels: Optional[list[str]] = None


class RubricConfigResponse(BaseModel):
    """Schema for rubric configuration response."""

    id: int
    name: str
    is_default: bool
    min_description_words: int
    require_acceptance_criteria: bool
    allowed_labels: Optional[list[str]]
    rules: list[RubricRuleResponse]
    ambiguous_terms: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RubricConfigListResponse(BaseModel):
    """Schema for listing rubric configurations."""

    id: int
    name: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AmbiguousTermCreate(BaseModel):
    """Schema for adding an ambiguous term."""

    term: str = Field(..., min_length=2, max_length=100)


class PreviewScoreRequest(BaseModel):
    """Schema for previewing a score on sample data."""

    summary: str
    description: Optional[str] = None
    labels: list[str] = []
    estimate: Optional[float] = None


class PreviewScoreResponse(BaseModel):
    """Schema for preview score result."""

    score: float
    breakdown: dict[str, dict[str, Any]]
