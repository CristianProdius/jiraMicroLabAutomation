"""DSPy pipeline for issue analysis and feedback generation."""

import re
from dataclasses import dataclass
from typing import Any, Optional

import dspy
from rich.console import Console

from .config import AppConfig
from .exceptions import LLMError, ScoreValidationError
from .jira_client import JiraIssue
from .rubric import RubricEvaluator
from .signatures import AcceptanceCriteriaRefinement, IssueCritique

console = Console()


def sanitize_llm_input(text: str | None, max_length: int = 5000) -> str:
    """
    Sanitize user input before passing to LLM to prevent prompt injection.

    - Removes instruction-like patterns that could manipulate LLM behavior
    - Truncates to max length
    - Returns empty string for None input

    Args:
        text: Input text to sanitize
        max_length: Maximum length of output

    Returns:
        Sanitized text safe for LLM input
    """
    if not text:
        return ""

    # Truncate first to avoid regex on huge strings
    text = text[:max_length]

    # Remove common injection patterns (case-insensitive)
    injection_patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?)",
        r"(?i)disregard\s+(all\s+)?(previous|above|prior)",
        r"(?i)forget\s+(all\s+)?(previous|above|prior)",
        r"(?i)system\s*:\s*",
        r"(?i)assistant\s*:\s*",
        r"(?i)human\s*:\s*",
        r"(?i)user\s*:\s*",
        r"(?i)\[INST\]",
        r"(?i)\[/INST\]",
        r"(?i)</s>",
        r"(?i)<<SYS>>",
        r"(?i)<</SYS>>",
        r"(?i)<\|im_start\|>",
        r"(?i)<\|im_end\|>",
        r"(?i)<\|endoftext\|>",
    ]

    for pattern in injection_patterns:
        text = re.sub(pattern, "[filtered]", text)

    return text


@dataclass
class Feedback:
    """Complete feedback for an issue."""

    issue_key: str
    score: float  # 0-100
    emoji: str
    overall_assessment: str
    strengths: list[str]
    improvements: list[str]
    suggestions: list[str]
    rubric_breakdown: dict[str, dict[str, Any]]
    improved_ac: Optional[str] = None
    resources: Optional[list[str]] = None

    def __post_init__(self) -> None:
        if self.resources is None:
            self.resources = []
        # Normalize empty string to None
        if self.improved_ac == "":
            self.improved_ac = None
        # Validate score is in valid range
        if not (0 <= self.score <= 100):
            raise ScoreValidationError(f"Score must be 0-100, got {self.score}")


class FeedbackPipeline:
    """Main pipeline for generating issue feedback."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.rubric_evaluator = RubricEvaluator(config.rubric)

        # Initialize DSPy with configured model
        self._setup_dspy()

        # Create DSPy modules
        self.critique_module = dspy.ChainOfThought(IssueCritique)
        self.ac_refinement_module = dspy.ChainOfThought(AcceptanceCriteriaRefinement)

    def _setup_dspy(self):
        """Configure DSPy with the specified LLM."""
        model_name = self.config.model

        if model_name.startswith("gpt"):
            # OpenAI models
            if not self.config.openai_api_key:
                raise ValueError("OPENAI_API_KEY required for OpenAI models")

            lm = dspy.OpenAI(
                model=model_name,
                api_key=self.config.openai_api_key,
                temperature=0.7,
                max_tokens=1500
            )
        elif "claude" in model_name:
            # Anthropic models
            if not self.config.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY required for Claude models")

            lm = dspy.Claude(
                model=model_name,
                api_key=self.config.anthropic_api_key,
                temperature=0.7,
                max_tokens=1500
            )
        else:
            # Default fallback
            console.log(f"[yellow]Unknown model {model_name}, using OpenAI default[/yellow]")
            lm = dspy.OpenAI(
                model="gpt-4o-mini",
                api_key=self.config.openai_api_key,
                temperature=0.7
            )

        dspy.settings.configure(lm=lm)
        console.log(f"[dim]DSPy configured with model: {model_name}[/dim]")

    def generate_feedback(self, issue: JiraIssue) -> Feedback:
        """Generate complete feedback for an issue."""
        console.log(f"\n[bold cyan]Analyzing {issue.key}:[/bold cyan] {issue.summary}")

        # Step 1: Run deterministic rubric checks
        rubric_results = self.rubric_evaluator.evaluate(issue)
        rubric_score, rubric_breakdown = self.rubric_evaluator.calculate_final_score(rubric_results)

        console.log(f"[dim]Rubric score: {rubric_score}/100[/dim]")

        # Step 2: Format rubric findings for LLM
        rubric_findings = self._format_rubric_findings(rubric_results)

        # Step 3: Get LLM critique (with input sanitization)
        try:
            critique_result = self.critique_module(
                title=sanitize_llm_input(issue.summary, max_length=200),
                description=sanitize_llm_input(
                    issue.description or "No description provided", max_length=5000
                ),
                labels=sanitize_llm_input(
                    ", ".join(issue.labels) if issue.labels else "None", max_length=500
                ),
                estimate=str(issue.estimate) if issue.estimate else "None",
                issue_type=sanitize_llm_input(issue.issue_type, max_length=50),
                rubric_findings=rubric_findings,  # Generated internally, not user input
            )

            overall_assessment = critique_result.overall_assessment
            strengths = self._safe_parse_csv(critique_result.strengths)
            improvements = self._safe_parse_csv(critique_result.improvements)
            suggestions = self._parse_numbered_list(critique_result.actionable_suggestions)

        except (dspy.DSPyAssertionError, ValueError, TypeError, RuntimeError) as e:
            # LLM errors - fall back gracefully to rubric-only feedback
            console.log(f"[red]LLM critique failed: {e}[/red]")
            overall_assessment = f"Rubric score: {rubric_score}/100"
            strengths = ["Issue submitted for review"]
            improvements = [r.message for r in rubric_results if r.score < 0.7]
            suggestions = [r.suggestion for r in rubric_results if r.suggestion]

        # Step 4: Refine AC if needed (with input sanitization)
        improved_ac: str | None = None
        ac_result_raw = [r for r in rubric_results if r.rule_id == "acceptance_criteria"]
        if ac_result_raw and ac_result_raw[0].score < 1.0:
            try:
                ac_result = self.ac_refinement_module(
                    title=sanitize_llm_input(issue.summary, max_length=200),
                    description=sanitize_llm_input(issue.description or "", max_length=5000),
                    current_ac=sanitize_llm_input(
                        self._extract_ac(issue.description), max_length=2000
                    ),
                )
                improved_ac = ac_result.refined_ac
            except (dspy.DSPyAssertionError, ValueError, TypeError, RuntimeError) as e:
                console.log(f"[yellow]AC refinement failed: {e}[/yellow]")

        # Step 5: Determine emoji based on score
        emoji = self._get_score_emoji(rubric_score)

        feedback = Feedback(
            issue_key=issue.key,
            score=rubric_score,
            emoji=emoji,
            overall_assessment=overall_assessment,
            strengths=strengths[:4],  # Limit to 4
            improvements=improvements[:4],
            suggestions=suggestions[:5],  # Limit to 5
            rubric_breakdown=rubric_breakdown,
            improved_ac=improved_ac,
            resources=self._get_resources(issue, rubric_results)
        )

        console.log(f"[green]Feedback generated: {rubric_score}/100 {emoji}[/green]")
        return feedback

    def _format_rubric_findings(self, results: list) -> str:
        """Format rubric results for LLM input."""
        lines = []
        for r in results:
            status = "✓" if r.score >= 0.8 else "✗"
            lines.append(f"{status} {r.rule_id}: {r.message}")
            if r.suggestion:
                lines.append(f"  → {r.suggestion}")
        return "\n".join(lines)

    def _extract_ac(self, description: str) -> str:
        """Extract acceptance criteria from description."""
        if not description:
            return "None"

        # Try to find AC section
        lower_desc = description.lower()
        if "acceptance criteria" in lower_desc:
            idx = lower_desc.index("acceptance criteria")
            return description[idx:idx+500]  # Get section

        return "None explicitly stated"

    def _safe_parse_csv(self, text: str | None) -> list[str]:
        """Safely parse comma-separated values from LLM output."""
        if not text or not isinstance(text, str):
            return []
        return [s.strip() for s in text.split(",") if s.strip()]

    def _parse_numbered_list(self, text: str | None) -> list[str]:
        """Parse numbered list from LLM output."""
        if not text or not isinstance(text, str):
            return []
        items = []
        for line in text.split("\n"):
            line = line.strip()
            # Remove numbering (1., 1), etc.)
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                clean = line.lstrip("0123456789.-•) ").strip()
                if clean:
                    items.append(clean)
            elif line and not items:
                # First line might not be numbered
                items.append(line)
        return items

    def _get_score_emoji(self, score: float) -> str:
        """Get emoji based on score."""
        if score >= 90:
            return "🌟"
        elif score >= 80:
            return "✅"
        elif score >= 70:
            return "👍"
        elif score >= 60:
            return "⚠️"
        elif score >= 50:
            return "🔧"
        else:
            return "❌"

    def _get_resources(self, issue: JiraIssue, rubric_results: list) -> list[str]:
        """Generate helpful resources based on findings."""
        resources = []

        # Check what needs improvement
        for result in rubric_results:
            if result.score < 0.7:
                if result.rule_id == "acceptance_criteria":
                    resources.append("Learn about writing testable acceptance criteria: https://www.atlassian.com/agile/project-management/user-stories")
                elif result.rule_id == "title_clarity":
                    resources.append("Guide to writing clear issue titles: https://www.atlassian.com/agile/project-management/epics-stories-themes")
                elif result.rule_id == "ambiguous_terms":
                    resources.append("SMART criteria for requirement writing: https://en.wikipedia.org/wiki/SMART_criteria")

        return list(set(resources))[:3]  # Max 3 unique resources
