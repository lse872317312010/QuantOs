"""Human-readable analyst brief rendering."""

from __future__ import annotations

from quantos.contracts import DecisionCandidate
from quantos.workspace.engine import ReviewSession


def _candidate_lines(rank: int, candidate: DecisionCandidate) -> list[str]:
    lines = [
        f"## {rank}. {candidate.instrument} — {candidate.stance.value}",
        "",
        f"- State: **{candidate.state.value}**",
        f"- Confidence: **{candidate.confidence:.0%}**",
        f"- Decision score: **{candidate.decision_score:+.2f}**",
        f"- Review priority: **{candidate.priority_score:.3f}**",
        f"- Horizon: **{candidate.horizon}**",
        f"- Thesis: {candidate.thesis}",
    ]
    if candidate.risk.blockers:
        lines.append(f"- Blockers: {'; '.join(candidate.risk.blockers)}")
    if candidate.risk.warnings:
        lines.append(f"- Risk warnings: {'; '.join(candidate.risk.warnings)}")

    if candidate.supporting_evidence:
        lines.extend(["", "### Supporting evidence"])
        lines.extend(f"- {item}" for item in candidate.supporting_evidence)
    if candidate.contradicting_evidence:
        lines.extend(["", "### Contradicting evidence"])
        lines.extend(f"- {item}" for item in candidate.contradicting_evidence)
    if candidate.invalidation_conditions:
        lines.extend(["", "### Invalidation / reassessment conditions"])
        lines.extend(f"- {item}" for item in candidate.invalidation_conditions)
    if candidate.alternatives:
        lines.extend(["", "### Alternatives"])
        lines.extend(f"- {item}" for item in candidate.alternatives)
    lines.append("")
    return lines


def render_markdown(session: ReviewSession) -> str:
    """Render one review session without converting it into an execution ticket."""
    snapshot = session.snapshot
    lines = [
        "# QuantOs analyst review",
        "",
        f"As of: **{snapshot.as_of.isoformat()}**",
        "",
        "Ranked for human review only. This report is not an execution instruction.",
        "",
    ]

    if snapshot.market_context:
        lines.extend(["## Market context", ""])
        for key, value in sorted(snapshot.market_context.items()):
            lines.append(f"- {key}: {value}")
        lines.append("")

    lines.extend(["# Decision slate", ""])
    if not snapshot.candidates:
        lines.extend(["No candidates available.", ""])
    else:
        for rank, candidate in enumerate(snapshot.candidates, start=1):
            lines.extend(_candidate_lines(rank, candidate))

    if snapshot.alerts:
        lines.extend(["# Alerts", ""])
        lines.extend(f"- {item}" for item in snapshot.alerts)
        lines.append("")

    if session.failures:
        lines.extend(["# Provider failures", ""])
        lines.extend(
            f"- {failure.instrument} / {failure.stage} / {failure.provider}: {failure.error}"
            for failure in session.failures
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
