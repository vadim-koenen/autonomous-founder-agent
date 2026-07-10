"""Verified transaction accounting and capital allocation."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, List, Mapping

from .operator_models import RevenueSummary, TransactionRecord, transaction_from_dict


class RevenueVerificationError(ValueError):
    """Raised when a transaction cannot be counted as verified revenue."""


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def transaction_is_verified(transaction: TransactionRecord) -> bool:
    return bool(
        transaction.status == "completed"
        and transaction.transaction_id.strip()
        and transaction.verification_reference.strip()
        and transaction.verified_at.strip()
        and _money(transaction.gross_amount) > Decimal("0.00")
    )


def summarize_transactions(
    transactions: Iterable[TransactionRecord],
    currency: str = "USD",
) -> RevenueSummary:
    verified: List[TransactionRecord] = []
    seen_ids = set()
    for transaction in transactions:
        if not transaction_is_verified(transaction):
            continue
        if transaction.transaction_id in seen_ids:
            raise RevenueVerificationError("duplicate transaction id: {0}".format(transaction.transaction_id))
        if transaction.currency != currency:
            raise RevenueVerificationError(
                "currency conversion is not configured: {0}".format(transaction.currency)
            )
        seen_ids.add(transaction.transaction_id)
        verified.append(transaction)

    gross = sum((_money(item.gross_amount) for item in verified), Decimal("0.00"))
    processor_fees = sum((_money(item.processor_fees) for item in verified), Decimal("0.00"))
    platform_fees = sum((_money(item.platform_fees) for item in verified), Decimal("0.00"))
    refunds = sum((_money(item.refunds) for item in verified), Decimal("0.00"))
    direct_costs = sum((_money(item.direct_costs) for item in verified), Decimal("0.00"))
    net = gross - processor_fees - platform_fees - refunds - direct_costs
    allocatable = max(net, Decimal("0.00"))

    return RevenueSummary(
        currency=currency,
        verified_transactions=len(verified),
        gross_revenue=float(_money(gross)),
        processor_fees=float(_money(processor_fees)),
        platform_fees=float(_money(platform_fees)),
        refunds=float(_money(refunds)),
        direct_costs=float(_money(direct_costs)),
        net_revenue=float(_money(net)),
        physical_form_fund=float(_money(allocatable * Decimal("0.70"))),
        reinvestment_balance=float(_money(allocatable * Decimal("0.20"))),
        contingency_reserve=float(_money(allocatable * Decimal("0.10"))),
    )


def summarize_ledger(ledger: Mapping[str, object]) -> RevenueSummary:
    transactions = [transaction_from_dict(item) for item in ledger.get("transactions", [])]
    return summarize_transactions(transactions, currency=str(ledger.get("currency", "USD")))


def render_revenue_ledger(ledger: Mapping[str, object], summary: RevenueSummary) -> str:
    lines = [
        "# Revenue Ledger",
        "",
        "Only completed payments with a non-empty verification reference count as revenue.",
        "Public impressions, contacts, replies, and checkout starts never count as revenue.",
        "No buyer personal information or credentials are stored here.",
        "",
        "## Verified Summary",
        "",
        "| Metric | Amount |",
        "| --- | ---: |",
        "| Verified transactions | {0} |".format(summary.verified_transactions),
        "| Gross revenue | ${0:.2f} |".format(summary.gross_revenue),
        "| Processor fees | ${0:.2f} |".format(summary.processor_fees),
        "| Platform fees | ${0:.2f} |".format(summary.platform_fees),
        "| Refunds | ${0:.2f} |".format(summary.refunds),
        "| Direct costs | ${0:.2f} |".format(summary.direct_costs),
        "| Net revenue | ${0:.2f} |".format(summary.net_revenue),
        "| Physical-form fund (70%) | ${0:.2f} |".format(summary.physical_form_fund),
        "| Experiment balance (20%) | ${0:.2f} |".format(summary.reinvestment_balance),
        "| Fees/refunds reserve (10%) | ${0:.2f} |".format(summary.contingency_reserve),
        "",
        "## Transactions",
        "",
        "| Date | Experiment | Gross | Fees | Refunds | Costs | Verification | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]

    transactions = ledger.get("transactions", [])
    if not transactions:
        lines.append("| - | No verified transactions | $0.00 | $0.00 | $0.00 | $0.00 | - | pending |")
    else:
        for item in transactions:
            total_fees = float(item.get("processor_fees", 0)) + float(item.get("platform_fees", 0))
            verification = item.get("verification_reference", "") or "unverified"
            lines.append(
                "| {date} | {experiment} | ${gross:.2f} | ${fees:.2f} | ${refunds:.2f} | ${costs:.2f} | {verification} | {status} |".format(
                    date=item.get("occurred_at", ""),
                    experiment=item.get("experiment_id", ""),
                    gross=float(item.get("gross_amount", 0)),
                    fees=total_fees,
                    refunds=float(item.get("refunds", 0)),
                    costs=float(item.get("direct_costs", 0)),
                    verification=verification,
                    status=item.get("status", ""),
                )
            )

    lines.extend(
        [
            "",
            "## Capital Policy",
            "",
            "Verified positive net revenue is allocated 70% to the physical-form fund, 20% to experiments, and 10% to fees, refunds, and contingencies. This ledger does not move funds.",
            "",
        ]
    )
    return "\n".join(lines)
