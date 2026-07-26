"""Configuration loading and validation for the promotion engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG = Path("config/promotion_engine.json")


class PromotionConfigError(ValueError):
    """Raised when promotion configuration is incomplete or unsafe."""


def load_config(path: Path = DEFAULT_CONFIG) -> Dict[str, Any]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    campaign = config.get("campaign", {})
    policy = config.get("policy", {})
    segments = config.get("segments", [])

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

    serialized = json.dumps(config).lower()
    if "apollo_api_key" in serialized or "private_app_token" in serialized:
        raise PromotionConfigError("secrets must be supplied through environment variables")
    return config
