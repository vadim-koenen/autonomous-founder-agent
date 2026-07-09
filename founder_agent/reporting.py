"""Markdown and JSON report helpers for M1."""

from __future__ import annotations

import json
from typing import List

from .models import M1DecisionRun, ScoredStrategy, strategy_summary, to_plain_data
from .scoring import RUBRIC


def run_to_json(run: M1DecisionRun) -> str:
    return json.dumps(to_plain_data(run), indent=2, sort_keys=True)


def _table(rows: List[List[str]]) -> str:
    if not rows:
        return ""
    widths = [max(len(str(row[index])) for row in rows) for index in range(len(rows[0]))]
    output = []
    for row_index, row in enumerate(rows):
        output.append("| " + " | ".join(str(cell).ljust(widths[index]) for index, cell in enumerate(row)) + " |")
        if row_index == 0:
            output.append("| " + " | ".join("-" * widths[index] for index in range(len(row))) + " |")
    return "\n".join(output)


def _top_rows(strategies: List[ScoredStrategy]) -> List[List[str]]:
    rows = [["Rank", "Score", "Strategy", "Category", "First offer"]]
    for index, scored in enumerate(strategies, start=1):
        strategy = scored.strategy
        rows.append(
            [
                str(index),
                f"{scored.weighted_score:.2f}",
                strategy.name,
                strategy.category.value,
                strategy.first_offer,
            ]
        )
    return rows


def _candidate_rows(strategies: List[ScoredStrategy]) -> List[List[str]]:
    rows = [["Score", "ID", "Strategy", "Category", "Speed", "Sale", "Automation", "Risk"]]
    for scored in strategies:
        scores = scored.dimension_scores
        risk_pair = f"{scores['platform_risk_reverse']}/{scores['legal_compliance_risk_reverse']}"
        rows.append(
            [
                f"{scored.weighted_score:.2f}",
                scored.strategy.strategy_id,
                scored.strategy.name,
                scored.strategy.category.value,
                str(scores["speed_to_first_dollar"]),
                str(scores["probability_of_first_sale"]),
                str(scores["automation_leverage"]),
                risk_pair,
            ]
        )
    return rows


def render_markdown_run(run: M1DecisionRun) -> str:
    primary = run.primary_experiment.strategy
    launch = run.launch_plan
    lines: List[str] = [
        "# Autonomous Founder Agent M1 Example Run",
        "",
        f"As of: {run.as_of.isoformat()}",
        "",
        f"Mission: {run.mission}",
        "",
        f"External execution status: {run.m1_external_execution_status}",
        "",
        "## Scoring Rubric",
        "",
        "Scores are 1-10. For the two reverse-scored risk dimensions, 10 means lower risk.",
        "",
    ]
    rows = [["Dimension", "Weight", "Reverse scored", "Description"]]
    for dimension in RUBRIC:
        rows.append([dimension.label, f"{dimension.weight:.1f}", str(dimension.reverse_scored), dimension.description])
    lines.extend([_table(rows), "", "## Top 3 Strategies", "", _table(_top_rows(run.top_3)), ""])
    lines.extend(
        [
            "## Selected Primary Experiment",
            "",
            f"Selected: {primary.name}",
            "",
            f"Weighted score: {run.primary_experiment.weighted_score:.2f}",
            "",
            f"Thesis: {primary.thesis}",
            "",
            f"Target buyer: {primary.target_buyer}",
            "",
            f"First offer: {primary.first_offer}",
            "",
            f"Why it won: {primary.score_notes}",
            "",
            "## Concrete Launch Plan",
            "",
            f"Experiment: {launch.experiment_name}",
            "",
            f"Objective: {launch.objective}",
            "",
            f"Price test: {launch.price_test}",
            "",
            "Draft assets to build:",
        ]
    )
    lines.extend([f"- {item}" for item in launch.draft_assets_to_build])
    lines.extend(["", "Internal build steps:"])
    lines.extend([f"- {item}" for item in launch.internal_build_steps])
    lines.extend(["", "Validation steps before launch:"])
    lines.extend([f"- {item}" for item in launch.validation_steps_before_launch])
    lines.extend(["", "External actions required to launch:"])
    lines.extend([f"- [{item.action_type.value}] {item.description}" for item in launch.external_actions_required])
    lines.extend(["", "Approval checklist:"])
    lines.extend([f"- {item}" for item in launch.approval_checklist])
    lines.extend(["", "Stop conditions:"])
    lines.extend([f"- {item}" for item in launch.stop_conditions])
    lines.extend(["", "Reinvestment path toward physical form:"])
    lines.extend([f"- {item}" for item in launch.reinvestment_path])
    lines.extend(["", "M1 boundary statement:", "", launch.m1_boundary_statement, ""])
    lines.extend(["## All Candidate Strategies", "", _table(_candidate_rows(run.scored_candidates)), ""])
    lines.extend(["## Compact Top 3 Data", "", "```json", json.dumps([strategy_summary(item) for item in run.top_3], indent=2), "```", ""])
    return "\n".join(lines)
