"""Rubric configuration API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user
from api.auth.models import User
from api.rubrics.models import UserRubricConfig, RubricRule, AmbiguousTerm, DEFAULT_RUBRIC_RULES
from api.rubrics.schemas import (
    RubricConfigCreate,
    RubricConfigUpdate,
    RubricConfigResponse,
    RubricConfigListResponse,
    RubricRuleResponse,
    RubricRuleUpdate,
    AmbiguousTermCreate,
    PreviewScoreRequest,
    PreviewScoreResponse,
)
from api.issues.service import RubricService

router = APIRouter(prefix="/rubrics", tags=["Rubrics"])

# Rule metadata lookup
RULE_METADATA = {rule["rule_id"]: rule for rule in DEFAULT_RUBRIC_RULES}


def _build_config_response(config: UserRubricConfig) -> RubricConfigResponse:
    """Build a full rubric config response."""
    rules = [
        RubricRuleResponse(
            id=rule.id,
            rule_id=rule.rule_id,
            name=RULE_METADATA.get(rule.rule_id, {}).get("name", rule.rule_id),
            description=RULE_METADATA.get(rule.rule_id, {}).get("description", ""),
            weight=rule.weight,
            is_enabled=rule.is_enabled,
            thresholds=rule.thresholds,
        )
        for rule in config.rules
    ]

    terms = [term.term for term in config.ambiguous_terms]

    return RubricConfigResponse(
        id=config.id,
        name=config.name,
        is_default=config.is_default,
        min_description_words=config.min_description_words,
        require_acceptance_criteria=config.require_acceptance_criteria,
        allowed_labels=config.allowed_labels,
        rules=rules,
        ambiguous_terms=terms,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("", response_model=list[RubricConfigListResponse])
async def list_rubric_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all rubric configurations for the current user."""
    configs = (
        db.query(UserRubricConfig)
        .filter(UserRubricConfig.user_id == current_user.id)
        .order_by(UserRubricConfig.is_default.desc(), UserRubricConfig.name)
        .all()
    )

    return [
        RubricConfigListResponse(
            id=config.id,
            name=config.name,
            is_default=config.is_default,
            created_at=config.created_at,
        )
        for config in configs
    ]


@router.post("", response_model=RubricConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_rubric_config(
    data: RubricConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new rubric configuration."""
    config = UserRubricConfig(
        user_id=current_user.id,
        name=data.name,
        is_default=False,
        min_description_words=data.min_description_words,
        require_acceptance_criteria=data.require_acceptance_criteria,
        allowed_labels=data.allowed_labels,
    )
    db.add(config)
    db.flush()

    # Add default rules
    for rule_data in DEFAULT_RUBRIC_RULES:
        rule = RubricRule(
            config_id=config.id,
            rule_id=rule_data["rule_id"],
            weight=rule_data["weight"],
            is_enabled=True,
            thresholds=rule_data.get("thresholds"),
        )
        db.add(rule)

    # Add default ambiguous terms
    from api.rubrics.models import DEFAULT_AMBIGUOUS_TERMS
    for term in DEFAULT_AMBIGUOUS_TERMS:
        db.add(AmbiguousTerm(config_id=config.id, term=term))

    db.commit()
    db.refresh(config)

    return _build_config_response(config)


@router.get("/{config_id}", response_model=RubricConfigResponse)
async def get_rubric_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific rubric configuration."""
    config = (
        db.query(UserRubricConfig)
        .filter(
            UserRubricConfig.id == config_id,
            UserRubricConfig.user_id == current_user.id,
        )
        .first()
    )

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    return _build_config_response(config)


@router.put("/{config_id}", response_model=RubricConfigResponse)
async def update_rubric_config(
    config_id: int,
    data: RubricConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a rubric configuration."""
    config = (
        db.query(UserRubricConfig)
        .filter(
            UserRubricConfig.id == config_id,
            UserRubricConfig.user_id == current_user.id,
        )
        .first()
    )

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    if data.name is not None:
        config.name = data.name
    if data.min_description_words is not None:
        config.min_description_words = data.min_description_words
    if data.require_acceptance_criteria is not None:
        config.require_acceptance_criteria = data.require_acceptance_criteria
    if data.allowed_labels is not None:
        config.allowed_labels = data.allowed_labels

    db.commit()
    db.refresh(config)

    return _build_config_response(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rubric_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a rubric configuration."""
    config = (
        db.query(UserRubricConfig)
        .filter(
            UserRubricConfig.id == config_id,
            UserRubricConfig.user_id == current_user.id,
        )
        .first()
    )

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    if config.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default configuration",
        )

    db.delete(config)
    db.commit()


@router.post("/{config_id}/set-default", response_model=RubricConfigResponse)
async def set_default_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a configuration as the default."""
    config = (
        db.query(UserRubricConfig)
        .filter(
            UserRubricConfig.id == config_id,
            UserRubricConfig.user_id == current_user.id,
        )
        .first()
    )

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    # Unset current default
    db.query(UserRubricConfig).filter(
        UserRubricConfig.user_id == current_user.id,
        UserRubricConfig.is_default == True,
    ).update({"is_default": False})

    # Set new default
    config.is_default = True
    db.commit()
    db.refresh(config)

    return _build_config_response(config)


# ===================
# Rule Management
# ===================
@router.put("/{config_id}/rules/{rule_id}", response_model=RubricRuleResponse)
async def update_rule(
    config_id: int,
    rule_id: str,
    data: RubricRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a specific rule in a configuration."""
    # Verify config ownership
    config = (
        db.query(UserRubricConfig)
        .filter(
            UserRubricConfig.id == config_id,
            UserRubricConfig.user_id == current_user.id,
        )
        .first()
    )

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    # Find the rule
    rule = (
        db.query(RubricRule)
        .filter(
            RubricRule.config_id == config_id,
            RubricRule.rule_id == rule_id,
        )
        .first()
    )

    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    if data.weight is not None:
        rule.weight = data.weight
    if data.is_enabled is not None:
        rule.is_enabled = data.is_enabled
    if data.thresholds is not None:
        rule.thresholds = data.thresholds

    db.commit()
    db.refresh(rule)

    return RubricRuleResponse(
        id=rule.id,
        rule_id=rule.rule_id,
        name=RULE_METADATA.get(rule.rule_id, {}).get("name", rule.rule_id),
        description=RULE_METADATA.get(rule.rule_id, {}).get("description", ""),
        weight=rule.weight,
        is_enabled=rule.is_enabled,
        thresholds=rule.thresholds,
    )


# ===================
# Ambiguous Terms Management
# ===================
@router.get("/{config_id}/terms", response_model=list[str])
async def list_terms(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List ambiguous terms for a configuration."""
    config = (
        db.query(UserRubricConfig)
        .filter(
            UserRubricConfig.id == config_id,
            UserRubricConfig.user_id == current_user.id,
        )
        .first()
    )

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    return [term.term for term in config.ambiguous_terms]


@router.post("/{config_id}/terms", response_model=list[str], status_code=status.HTTP_201_CREATED)
async def add_term(
    config_id: int,
    data: AmbiguousTermCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add an ambiguous term to a configuration."""
    config = (
        db.query(UserRubricConfig)
        .filter(
            UserRubricConfig.id == config_id,
            UserRubricConfig.user_id == current_user.id,
        )
        .first()
    )

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    # Check if term already exists
    existing = (
        db.query(AmbiguousTerm)
        .filter(
            AmbiguousTerm.config_id == config_id,
            AmbiguousTerm.term == data.term.lower(),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Term already exists",
        )

    term = AmbiguousTerm(config_id=config_id, term=data.term.lower())
    db.add(term)
    db.commit()

    return [t.term for t in config.ambiguous_terms]


@router.delete("/{config_id}/terms/{term}", response_model=list[str])
async def delete_term(
    config_id: int,
    term: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove an ambiguous term from a configuration."""
    config = (
        db.query(UserRubricConfig)
        .filter(
            UserRubricConfig.id == config_id,
            UserRubricConfig.user_id == current_user.id,
        )
        .first()
    )

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    term_record = (
        db.query(AmbiguousTerm)
        .filter(
            AmbiguousTerm.config_id == config_id,
            AmbiguousTerm.term == term.lower(),
        )
        .first()
    )

    if not term_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")

    db.delete(term_record)
    db.commit()
    db.refresh(config)

    return [t.term for t in config.ambiguous_terms]


# ===================
# Preview
# ===================
@router.post("/{config_id}/preview", response_model=PreviewScoreResponse)
async def preview_score(
    config_id: int,
    data: PreviewScoreRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview scoring on sample issue data."""
    rubric_service = RubricService(db, current_user.id)
    config = rubric_service.get_config_by_id(config_id)

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    # Create a mock JiraIssue-like object
    from src.jira_client import JiraIssue
    from src.rubric import RubricEvaluator

    # Build minimal issue data
    mock_issue_data = {
        "key": "PREVIEW-1",
        "fields": {
            "summary": data.summary,
            "description": data.description or "",
            "labels": data.labels,
            "issuetype": {"name": "Story"},
            "status": {"name": "To Do"},
            "assignee": None,
        },
    }

    if data.estimate:
        mock_issue_data["fields"]["customfield_10016"] = data.estimate

    issue = JiraIssue(mock_issue_data)

    # Run evaluation
    rubric_config = rubric_service.to_rubric_config(config)
    evaluator = RubricEvaluator(rubric_config)
    results = evaluator.evaluate(issue)
    score, breakdown = evaluator.calculate_final_score(results)

    return PreviewScoreResponse(score=score, breakdown=breakdown)
