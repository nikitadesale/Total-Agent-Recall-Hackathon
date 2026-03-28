"""
Sentinel Twin — Reconciliation Engine
Validates actions against the user's health + finance vault.
All reasoning is stateless; no data is persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FinanceProfile:
    account_id: str
    daily_disposable_limit: float
    spent_today: float
    currency: str
    liquidity_status: str

    @property
    def remaining_budget(self) -> float:
        return round(self.daily_disposable_limit - self.spent_today, 2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FinanceProfile":
        return cls(
            account_id=data["account_id"],
            daily_disposable_limit=data["daily_disposable_limit"],
            spent_today=data["spent_today"],
            currency=data["currency"],
            liquidity_status=data["liquidity_status"],
        )


@dataclass
class HealthProfile:
    subject: str
    calories_max: int
    calories_consumed: int
    allergies: list[str]
    dietary: str

    @property
    def remaining_calories(self) -> int:
        return self.calories_max - self.calories_consumed

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealthProfile":
        return cls(
            subject=data["subject"],
            calories_max=data["nutritional_targets"]["calories_max"],
            calories_consumed=data["nutritional_targets"]["calories_consumed"],
            allergies=[a.lower() for a in data["restrictions"]["allergies"]],
            dietary=data["restrictions"]["dietary"],
        )


@dataclass
class ValidationResult:
    status: str          # "APPROVED" | "REJECTED"
    reason: str
    alternative: str


def _check_budget(cost: float, finance: FinanceProfile) -> str | None:
    if cost > finance.remaining_budget:
        return (
            f"Cost ${cost:.2f} exceeds remaining daily budget "
            f"${finance.remaining_budget:.2f} {finance.currency}."
        )
    return None


def _check_calories(calories: int, health: HealthProfile) -> str | None:
    if calories > health.remaining_calories:
        return (
            f"This item adds {calories} kcal but only "
            f"{health.remaining_calories} kcal remain for today."
        )
    return None


def _check_allergens(
    ingredients: list[str], health: HealthProfile
) -> str | None:
    hits = set(i.lower() for i in ingredients) & set(health.allergies)
    if hits:
        flagged = ", ".join(sorted(hits))
        return f"Allergen conflict detected: {flagged}."
    return None


def _build_alternative(
    action_type: str,
    budget_fail: bool,
    calorie_fail: bool,
    allergen_fail: bool,
    finance: FinanceProfile,
    health: HealthProfile,
) -> str:
    tips: list[str] = []

    if budget_fail:
        tips.append(
            f"Choose an item under ${finance.remaining_budget:.2f} "
            f"{finance.currency}."
        )
    if calorie_fail:
        tips.append(
            f"Look for options under {health.remaining_calories} kcal."
        )
    if allergen_fail:
        avoid = ", ".join(health.allergies)
        tips.append(f"Avoid ingredients containing: {avoid}.")

    if action_type == "food_order" and not tips:
        return "No alternative needed — action is fully compliant."

    return " ".join(tips) if tips else "Consider a lighter, budget-friendly option."


def reconcile_action(
    action: dict[str, Any],
    finance: FinanceProfile,
    health: HealthProfile,
) -> ValidationResult:
    """
    Core reconciliation: runs all constraint checks and returns a
    structured ValidationResult. Stateless — never writes to disk.
    """
    action_type = action.get("action_type", "unknown")
    cost = float(action.get("cost", 0))
    calories = int(action.get("calories", 0))
    ingredients: list[str] = action.get("ingredients", [])

    budget_err = _check_budget(cost, finance)
    calorie_err = _check_calories(calories, health)
    allergen_err = _check_allergens(ingredients, health)

    failures = [e for e in (budget_err, calorie_err, allergen_err) if e]

    if failures:
        alt = _build_alternative(
            action_type,
            budget_fail=budget_err is not None,
            calorie_fail=calorie_err is not None,
            allergen_fail=allergen_err is not None,
            finance=finance,
            health=health,
        )
        return ValidationResult(
            status="REJECTED",
            reason=" | ".join(failures),
            alternative=alt,
        )

    return ValidationResult(
        status="APPROVED",
        reason="All constraints satisfied: budget, calories, and allergens.",
        alternative="No alternative needed — action is fully compliant.",
    )
