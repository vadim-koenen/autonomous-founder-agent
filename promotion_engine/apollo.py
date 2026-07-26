"""Narrow Apollo API adapter. Sending and sequence activation are intentionally absent."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


APOLLO_BASE_URL = "https://api.apollo.io"


class ApolloAccessError(RuntimeError):
    """Raised when Apollo access or an outbound mutation is not authorized."""


class ApolloClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        grants_path: Path = Path("config/capability_grants.json"),
        timeout_seconds: int = 20,
    ):
        self.api_key = api_key or os.environ.get("APOLLO_API_KEY", "")
        self.grants_path = Path(grants_path)
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise ApolloAccessError("APOLLO_API_KEY is not configured")

    def _request(
        self, method: str, path: str, payload: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Any]:
        if not path.startswith("/") or "://" in path:
            raise ApolloAccessError("Apollo request path must be relative")
        body = None if payload is None else json.dumps(dict(payload)).encode("utf-8")
        request = Request(
            APOLLO_BASE_URL + path,
            data=body,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "x-api-key": self.api_key,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {"ok": True}
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise ApolloAccessError(
                "Apollo returned HTTP {0}: {1}".format(error.code, detail)
            ) from error
        except URLError as error:
            raise ApolloAccessError("Apollo request failed: {0}".format(error.reason)) from error

    def _require_write_grant(self, capability_id: str, environment_flag: str) -> None:
        grants = json.loads(self.grants_path.read_text(encoding="utf-8")).get("grants", [])
        grant = next((item for item in grants if item.get("capability_id") == capability_id), None)
        if not grant or grant.get("enabled") is not True:
            raise ApolloAccessError("{0} capability is disabled".format(capability_id))
        if os.environ.get(environment_flag, "").strip().lower() != "true":
            raise ApolloAccessError("{0} is not explicitly enabled".format(environment_flag))

    def _require_read_grant(self) -> None:
        grants = json.loads(self.grants_path.read_text(encoding="utf-8")).get("grants", [])
        grant = next(
            (
                item
                for item in grants
                if item.get("capability_id") == "apollo_read_and_enrich"
            ),
            None,
        )
        if not grant or grant.get("enabled") is not True:
            raise ApolloAccessError("apollo_read_and_enrich capability is disabled")

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/auth/health")

    def search_people(self, filters: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_read_grant()
        return self._request("POST", "/api/v1/mixed_people/api_search", filters)

    def enrich_person(self, filters: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_read_grant()
        if os.environ.get("APOLLO_ENRICHMENT_ENABLED", "").strip().lower() != "true":
            raise ApolloAccessError(
                "APOLLO_ENRICHMENT_ENABLED must be true because enrichment may consume credits"
            )
        return self._request("POST", "/api/v1/people/match", filters)

    def create_contact(self, contact: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_write_grant("apollo_contact_sync", "APOLLO_WRITE_ENABLED")
        query = urlencode({"run_dedupe": "true"})
        return self._request("POST", "/api/v1/contacts?{0}".format(query), contact)

    def add_contact_to_sequence_paused(
        self,
        sequence_id: str,
        contact_id: str,
        email_account_id: str,
    ) -> Dict[str, Any]:
        self._require_write_grant(
            "apollo_sequence_enrollment", "APOLLO_SEQUENCE_ENROLLMENT_ENABLED"
        )
        if not all(value.strip() for value in (sequence_id, contact_id, email_account_id)):
            raise ApolloAccessError("sequence, contact, and email account IDs are required")
        return self._request(
            "POST",
            "/api/v1/emailer_campaigns/{0}/add_contact_ids".format(sequence_id),
            {
                "contact_ids": [contact_id],
                "send_email_from_email_account_id": email_account_id,
                "contact_status": "paused",
            },
        )
