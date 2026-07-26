"""Configuration loading and validation for the promotion engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .store import SUPPRESSION_REASONS, SUPPRESSION_SCOPE_REASONS


DEFAULT_CONFIG = Path("config/promotion_engine.json")
APOLLO_ACTIVATION_GATES = (
    "sender_mailbox_verified",
    "message_authentication_verified",
    "postal_identity_configured",
    "unsubscribe_verified",
    "reply_bounce_stop_rules_verified",
)


class PromotionConfigError(ValueError):
    """Raised when promotion configuration is incomplete or unsafe."""


def load_config(path: Path = DEFAULT_CONFIG) -> Dict[str, Any]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    campaign = config.get("campaign", {})
    policy = config.get("policy", {})
    segments = config.get("segments", [])
    channels = config.get("channels", {})

    required_campaign = ("campaign_id", "site_url", "score_threshold")
    missing = [key for key in required_campaign if not campaign.get(key)]
    if missing:
        raise PromotionConfigError("missing campaign fields: {0}".format(", ".join(missing)))
    if not str(campaign["site_url"]).startswith("https://"):
        raise PromotionConfigError("campaign.site_url must use https")
    if not segments:
        raise PromotionConfigError("at least one segment is required")
    if not policy.get("allowed_countries"):
        raise PromotionConfigError("policy.allowed_countries must be explicit")

    for segment in segments:
        for key in ("segment_id", "label", "landing_path", "pain", "offer"):
            if not segment.get(key):
                raise PromotionConfigError(
                    "segment {0} missing {1}".format(segment.get("segment_id", "?"), key)
                )
        if not str(segment["landing_path"]).startswith("/"):
            raise PromotionConfigError("segment landing paths must be site-relative")
        groups = segment.get("required_technology_groups", [])
        if not groups or any(not group for group in groups):
            raise PromotionConfigError(
                "segment {0} requires explicit technology groups".format(
                    segment["segment_id"]
                )
            )

    segment_ids = {str(segment["segment_id"]) for segment in segments}
    active_segment_ids = campaign.get("active_segment_ids", [])
    if not active_segment_ids:
        raise PromotionConfigError("campaign.active_segment_ids must be explicit")
    unknown_active = sorted(set(active_segment_ids) - segment_ids)
    if unknown_active:
        raise PromotionConfigError(
            "unknown active segment ids: {0}".format(", ".join(unknown_active))
        )
    if not policy.get("allowed_approvers"):
        raise PromotionConfigError("policy.allowed_approvers must be explicit")
    configured_suppressions = set(policy.get("suppression_reasons", []))
    if configured_suppressions != set(SUPPRESSION_REASONS):
        raise PromotionConfigError(
            "policy.suppression_reasons must match the supported suppression set"
        )
    configured_scopes = policy.get("required_suppression_snapshot_scopes", [])
    if (
        not isinstance(configured_scopes, list)
        or any(not isinstance(scope, str) for scope in configured_scopes)
        or len(configured_scopes) != len(set(configured_scopes))
        or set(configured_scopes) != set(SUPPRESSION_SCOPE_REASONS)
    ):
        raise PromotionConfigError(
            "policy.required_suppression_snapshot_scopes must match the supported scope set"
        )
    try:
        maximum_snapshot_age = float(
            policy.get("suppression_snapshot_max_age_hours", 0)
        )
    except (TypeError, ValueError) as error:
        raise PromotionConfigError(
            "policy.suppression_snapshot_max_age_hours must be positive"
        ) from error
    if maximum_snapshot_age <= 0:
        raise PromotionConfigError(
            "policy.suppression_snapshot_max_age_hours must be positive"
        )

    email_channel = channels.get("apollo_email")
    if not isinstance(email_channel, dict):
        raise PromotionConfigError("channels.apollo_email must be configured")
    for flag in ("send_enabled", "sequence_activation_implemented"):
        if type(email_channel.get(flag)) is not bool:
            raise PromotionConfigError(
                "channels.apollo_email.{0} must be boolean".format(flag)
            )
    gates = email_channel.get("activation_gates")
    if not isinstance(gates, dict) or set(gates) != set(APOLLO_ACTIVATION_GATES):
        raise PromotionConfigError(
            "channels.apollo_email.activation_gates must contain the exact required gate set"
        )
    if any(type(gates[gate]) is not bool for gate in APOLLO_ACTIVATION_GATES):
        raise PromotionConfigError(
            "channels.apollo_email.activation_gates values must be boolean"
        )
    daily_limit = email_channel.get("default_daily_send_limit_after_activation")
    if type(daily_limit) is not int or daily_limit <= 0:
        raise PromotionConfigError(
            "channels.apollo_email.default_daily_send_limit_after_activation "
            "must be a positive integer"
        )

    serialized = json.dumps(config).lower()
    if "apollo_api_key" in serialized or "private_app_token" in serialized:
        raise PromotionConfigError("secrets must be supplied through environment variables")
    return config
