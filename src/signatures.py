"""DSPy signatures for issue analysis."""

import dspy


class IssueCritique(dspy.Signature):
    """Analyze a Jira issue and provide constructive feedback."""

    # The input that we call the LLM 
    title: str = dspy.InputField(desc="Issue title/summary")
    description: str = dspy.InputField(desc="Issue description")
    labels: str = dspy.InputField(desc="Comma-separated labels")
    estimate: str = dspy.InputField(desc="Story points or time estimate")
    issue_type: str = dspy.InputField(desc="Issue type (Story, Bug, Task, etc.)")
    rubric_findings: str = dspy.InputField(desc="Deterministic rubric evaluation findings")

    # Here is what AI will output us back
    overall_assessment: str = dspy.OutputField(
        desc="1-2 sentence summary of issue quality and main concerns"
    )
    strengths: str = dspy.OutputField(
        desc="Comma-separated list of strengths (2-4 specific items)"
    )
    improvements: str = dspy.OutputField(
        desc="Comma-separated list of areas needing improvement (2-4 specific items)"
    )
    actionable_suggestions: str = dspy.OutputField(
        desc="Numbered list of specific, actionable suggestions (3-5 items)"
    )


class AcceptanceCriteriaRefinement(dspy.Signature):
    """Refine acceptance criteria to be more testable."""

    # Input fields
    title: str = dspy.InputField(desc="Issue title")
    description: str = dspy.InputField(desc="Current issue description")
    current_ac: str = dspy.InputField(desc="Current acceptance criteria (if any)")

    # Output fields
    refined_ac: str = dspy.OutputField(
        desc="Improved acceptance criteria in Given/When/Then format or testable checklist"
    )
