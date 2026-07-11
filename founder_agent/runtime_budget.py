"""Per-cycle resource limits for the autonomous founder runtime."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping


RESOURCE_NAMES = (
    "source_fetches",
    "model_calls",
    "new_opportunities",
    "channel_candidates",
    "publications",
    "external_messages",
    "repository_writes",
    "spend_usd",
    "runtime_minutes",
)


class BudgetExceededError(RuntimeError):
    """Raised before an action would exceed its per-cycle allowance."""


@dataclass(frozen=True)
class RuntimeBudget:
    source_fetches: int
    model_calls: int
    new_opportunities: int
    channel_candidates: int
    publications: int
    external_messages: int
    repository_writes: int
    spend_usd: float
    runtime_minutes: int

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RuntimeBudget":
        limits = data.get("limits", data)
        missing = set(RESOURCE_NAMES) - set(limits)
        if missing:
            raise ValueError("runtime budget is missing limits: {0}".format(sorted(missing)))
        values: Dict[str, Any] = {}
        for name in RESOURCE_NAMES:
            value = limits[name]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                raise ValueError("runtime budget values must be non-negative numbers")
            values[name] = float(value) if name == "spend_usd" else int(value)
        return cls(**values)

    def as_dict(self) -> Dict[str, float | int]:
        return {name: getattr(self, name) for name in RESOURCE_NAMES}


class BudgetTracker:
    """Fail-closed accounting for every bounded runtime resource."""

    def __init__(self, budget: RuntimeBudget) -> None:
        self.budget = budget
        self.used: Dict[str, float] = {name: 0.0 for name in RESOURCE_NAMES}

    def consume(self, resource: str, amount: float = 1.0) -> None:
        if resource not in self.used:
            raise KeyError("unknown runtime budget resource: {0}".format(resource))
        if not isinstance(amount, (int, float)) or not math.isfinite(float(amount)) or amount < 0:
            raise ValueError("budget consumption cannot be negative")
        limit = float(getattr(self.budget, resource))
        proposed = self.used[resource] + float(amount)
        if proposed > limit:
            raise BudgetExceededError(
                "{0} budget exceeded: proposed={1} limit={2}".format(resource, proposed, limit)
            )
        self.used[resource] = proposed

    def remaining(self, resource: str) -> float:
        if resource not in self.used:
            raise KeyError("unknown runtime budget resource: {0}".format(resource))
        return round(float(getattr(self.budget, resource)) - self.used[resource], 4)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "limits": self.budget.as_dict(),
            "used": {
                name: round(value, 4) if name in {"spend_usd", "runtime_minutes"} else int(value)
                for name, value in self.used.items()
            },
            "remaining": {
                name: self.remaining(name)
                if name in {"spend_usd", "runtime_minutes"}
                else int(self.remaining(name))
                for name in RESOURCE_NAMES
            },
        }
