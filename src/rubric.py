"""Rubric-based issue evaluation rules."""

import re
from dataclasses import dataclass
from typing import Optional

from .config import RubricConfig
from .jira_client import JiraIssue


@dataclass
class RubricResult:
    """Result of a single rubric rule evaluation."""

    rule_id: str
    score: float  # 0.0 to 1.0
    message: str
    suggestion: str
    weight: float = 1.0


class RubricEvaluator:
    """Deterministic rubric-based evaluation of Jira issues."""

    def __init__(self, config: RubricConfig):
        self.config = config

    def evaluate(self, issue: JiraIssue) -> list[RubricResult]:
        """Run all rubric rules on an issue."""
        results = []

        results.append(self._check_title_clarity(issue))
        results.append(self._check_description_length(issue))
        results.append(self._check_acceptance_criteria(issue))
        results.append(self._check_ambiguous_terms(issue))
        results.append(self._check_estimate_present(issue))
        results.append(self._check_labels(issue))
        results.append(self._check_scope_clarity(issue))

        return results

    def _check_title_clarity(self, issue: JiraIssue) -> RubricResult:
        """Check if title is clear and actionable."""
        title = issue.summary.strip()

        # Check for filler words
        filler_words = ["just", "maybe", "perhaps", "kinda", "sort of"]
        has_filler = any(word in title.lower() for word in filler_words)

        # Check for outcome/action words
        action_words = ["add", "fix", "create", "update", "remove", "implement", "refactor"]
        has_action = any(word in title.lower() for word in action_words)

        # Check length
        is_too_short = len(title) < 10
        is_too_long = len(title) > 100

        score = 1.0
        issues = []

        if has_filler:
            score -= 0.3
            issues.append("contains filler words")

        if not has_action:
            score -= 0.2
            issues.append("lacks action verb")

        if is_too_short:
            score -= 0.3
            issues.append("too short")

        if is_too_long:
            score -= 0.2
            issues.append("too long")

        score = max(0.0, score)

        if score < 1.0:
            message = f"Title quality issues: {', '.join(issues)}"
            suggestion = "Rewrite title to be concise, actionable, and specific (e.g., 'Add user authentication to login page')"
        else:
            message = "Title is clear and actionable"
            suggestion = ""

        return RubricResult(
            rule_id="title_clarity",
            score=score,
            message=message,
            suggestion=suggestion,
            weight=1.0
        )

    def _check_description_length(self, issue: JiraIssue) -> RubricResult:
        """Check if description meets minimum word count."""
        description = issue.description.strip()
        words = [w for w in description.split() if len(w) > 0]
        word_count = len(words)

        min_words = self.config.min_description_words

        if word_count == 0:
            score = 0.0
            message = "Description is empty"
            suggestion = f"Add a description with at least {min_words} words explaining the problem and solution"
        elif word_count < min_words:
            score = word_count / min_words
            message = f"Description too short: {word_count}/{min_words} words"
            suggestion = f"Expand description to at least {min_words} words with more context and details"
        else:
            score = 1.0
            message = f"Description length adequate: {word_count} words"
            suggestion = ""

        return RubricResult(
            rule_id="description_length",
            score=score,
            message=message,
            suggestion=suggestion,
            weight=1.2
        )

    def _check_acceptance_criteria(self, issue: JiraIssue) -> RubricResult:
        """Check for presence of acceptance criteria."""
        description = issue.description.lower()

        # Look for AC patterns
        ac_patterns = [
            r"acceptance criteria",
            r"ac:",
            r"given.*when.*then",
            r"\[ \].*\[ \]",  # Checkboxes
            r"requirements:",
            r"must:",
        ]

        has_ac = any(re.search(pattern, description) for pattern in ac_patterns)

        if not self.config.require_acceptance_criteria:
            # If AC not required, just give a bonus for having them
            if has_ac:
                score = 1.0
                message = "Acceptance criteria present (optional)"
                suggestion = ""
            else:
                score = 0.8
                message = "No acceptance criteria (optional)"
                suggestion = "Consider adding testable acceptance criteria"
        else:
            if has_ac:
                score = 1.0
                message = "Acceptance criteria present"
                suggestion = ""
            else:
                score = 0.0
                message = "Acceptance criteria required but missing"
                suggestion = "Add acceptance criteria in Given/When/Then format or as a checklist"

        return RubricResult(
            rule_id="acceptance_criteria",
            score=score,
            message=message,
            suggestion=suggestion,
            weight=1.5
        )

    def _check_ambiguous_terms(self, issue: JiraIssue) -> RubricResult:
        """Check for ambiguous/vague terms."""
        text = f"{issue.summary} {issue.description}".lower()
        found_terms = []

        for term in self.config.ambiguous_terms:
            if term.lower() in text:
                found_terms.append(term)

        if not found_terms:
            score = 1.0
            message = "No ambiguous terms detected"
            suggestion = ""
        else:
            # Deduct points based on number of ambiguous terms
            score = max(0.0, 1.0 - (len(found_terms) * 0.15))
            message = f"Ambiguous terms found: {', '.join(set(found_terms))}"
            suggestion = "Replace vague terms with specific, measurable criteria (e.g., 'reduce load time from 3s to 1s' instead of 'optimize performance')"

        return RubricResult(
            rule_id="ambiguous_terms",
            score=score,
            message=message,
            suggestion=suggestion,
            weight=1.0
        )

    def _check_estimate_present(self, issue: JiraIssue) -> RubricResult:
        """Check if estimate is present."""
        estimate = issue.estimate

        if estimate is not None and estimate > 0:
            score = 1.0
            message = f"Estimate present: {estimate}"
            suggestion = ""
        else:
            score = 0.5
            message = "No estimate provided"
            suggestion = "Add story points or time estimate to help with planning"

        return RubricResult(
            rule_id="estimate_present",
            score=score,
            message=message,
            suggestion=suggestion,
            weight=0.8
        )

    def _check_labels(self, issue: JiraIssue) -> RubricResult:
        """Check if labels are appropriate."""
        labels = issue.labels

        if not self.config.allowed_labels:
            # No label restrictions, just check for presence
            if labels:
                score = 1.0
                message = f"Labels present: {', '.join(labels)}"
                suggestion = ""
            else:
                score = 0.7
                message = "No labels"
                suggestion = "Add relevant labels for categorization"
        else:
            # Check against allowed list
            valid_labels = [l for l in labels if l in self.config.allowed_labels]
            invalid_labels = [l for l in labels if l not in self.config.allowed_labels]

            if labels and not invalid_labels:
                score = 1.0
                message = f"All labels valid: {', '.join(labels)}"
                suggestion = ""
            elif invalid_labels:
                score = 0.5
                message = f"Invalid labels: {', '.join(invalid_labels)}"
                suggestion = f"Use only allowed labels: {', '.join(self.config.allowed_labels)}"
            else:
                score = 0.6
                message = "No labels"
                suggestion = f"Add labels from: {', '.join(self.config.allowed_labels)}"

        return RubricResult(
            rule_id="labels",
            score=score,
            message=message,
            suggestion=suggestion,
            weight=0.7
        )

    def _check_scope_clarity(self, issue: JiraIssue) -> RubricResult:
        """Check if scope is clearly defined."""
        description = issue.description.lower()

        # Look for scope indicators
        scope_indicators = [
            r"out of scope",
            r"in scope",
            r"dependencies:",
            r"blocked by",
            r"requires",
            r"affects",
        ]

        has_scope_info = any(re.search(pattern, description) for pattern in scope_indicators)

        # Check for overly broad scope words
        broad_words = ["everything", "all", "any", "complete", "total", "entire"]
        has_broad_words = any(word in description for word in broad_words)

        score = 1.0

        if has_scope_info:
            score = 1.0
            message = "Scope information present"
            suggestion = ""
        elif has_broad_words:
            score = 0.4
            message = "Scope appears too broad"
            suggestion = "Narrow scope to specific, deliverable changes. List dependencies or blockers if any."
        else:
            score = 0.7
            message = "Scope could be clearer"
            suggestion = "Clarify what is in/out of scope and list any dependencies"

        return RubricResult(
            rule_id="scope_clarity",
            score=score,
            message=message,
            suggestion=suggestion,
            weight=1.0
        )

    def calculate_final_score(self, results: list[RubricResult]) -> tuple[float, dict]:
        """
        Calculate weighted final score (0-100) and breakdown.

        Returns:
            (final_score, category_breakdown)
        """
        if not results:
            return 0.0, {}

        # Calculate weighted average
        total_weight = sum(r.weight for r in results)
        weighted_sum = sum(r.score * r.weight for r in results)
        final_score = (weighted_sum / total_weight) * 100 if total_weight > 0 else 0.0

        # Create breakdown by category
        breakdown = {
            result.rule_id: {
                "score": round(result.score * 100, 1),
                "message": result.message,
                "suggestion": result.suggestion
            }
            for result in results
        }

        return round(final_score, 1), breakdown
