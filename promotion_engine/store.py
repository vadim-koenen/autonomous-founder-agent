"""Private SQLite persistence for prospects, approvals, and outcome signals."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


class PromotionStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS prospects (
                prospect_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                email_hash TEXT NOT NULL UNIQUE,
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                email_status TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                seniority TEXT NOT NULL DEFAULT '',
                company TEXT NOT NULL DEFAULT '',
                company_domain TEXT NOT NULL DEFAULT '',
                company_size TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                industry TEXT NOT NULL DEFAULT '',
                technologies_json TEXT NOT NULL DEFAULT '[]',
                source_url TEXT NOT NULL DEFAULT '',
                evidence_note TEXT NOT NULL DEFAULT '',
                apollo_person_id TEXT NOT NULL DEFAULT '',
                apollo_contact_id TEXT NOT NULL DEFAULT '',
                lifecycle_status TEXT NOT NULL DEFAULT 'imported',
                imported_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS suppressions (
                email_hash TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                evidence_reference TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scores (
                prospect_id TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                segment_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                details_json TEXT NOT NULL,
                blockers_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                qualification_status TEXT NOT NULL,
                scored_at TEXT NOT NULL,
                PRIMARY KEY (prospect_id, campaign_id),
                FOREIGN KEY (prospect_id) REFERENCES prospects(prospect_id)
            );
            CREATE TABLE IF NOT EXISTS drafts (
                draft_id TEXT PRIMARY KEY,
                prospect_id TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                segment_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                wait_business_days INTEGER NOT NULL DEFAULT 0,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                attributed_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                approved_by TEXT NOT NULL DEFAULT '',
                approved_at TEXT NOT NULL DEFAULT '',
                exported_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE (prospect_id, campaign_id, channel, step_index),
                FOREIGN KEY (prospect_id) REFERENCES prospects(prospect_id)
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                prospect_id TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                channel TEXT NOT NULL,
                evidence_reference TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (prospect_id) REFERENCES prospects(prospect_id)
            );
            CREATE TABLE IF NOT EXISTS exports (
                export_id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                file_name TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def upsert_prospect(self, record: Mapping[str, Any]) -> str:
        email = str(record.get("email") or "").strip().lower()
        if not email:
            raise ValueError("email is required")
        prospect_id = hashlib.sha256(email.encode("utf-8")).hexdigest()[:24]
        now = utc_now()
        technologies = record.get("technologies", [])
        if isinstance(technologies, str):
            technologies = [
                item.strip()
                for item in technologies.replace("|", ",").replace(";", ",").split(",")
                if item.strip()
            ]
        values = {
            "prospect_id": prospect_id,
            "email": email,
            "email_hash": email_hash(email),
            "first_name": str(record.get("first_name") or "").strip(),
            "last_name": str(record.get("last_name") or "").strip(),
            "email_status": str(record.get("email_status") or "").strip(),
            "title": str(record.get("title") or "").strip(),
            "seniority": str(record.get("seniority") or "").strip(),
            "company": str(record.get("company") or "").strip(),
            "company_domain": str(record.get("company_domain") or "").strip().lower(),
            "company_size": str(record.get("company_size") or "").strip(),
            "country": str(record.get("country") or "").strip(),
            "industry": str(record.get("industry") or "").strip(),
            "technologies_json": json.dumps(technologies),
            "source_url": str(record.get("source_url") or "").strip(),
            "evidence_note": str(record.get("evidence_note") or "").strip(),
            "apollo_person_id": str(record.get("apollo_person_id") or "").strip(),
            "apollo_contact_id": str(record.get("apollo_contact_id") or "").strip(),
            "imported_at": now,
            "updated_at": now,
        }
        self.connection.execute(
            """
            INSERT INTO prospects (
                prospect_id, email, email_hash, first_name, last_name, email_status,
                title, seniority, company, company_domain, company_size, country,
                industry, technologies_json, source_url, evidence_note,
                apollo_person_id, apollo_contact_id, imported_at, updated_at
            ) VALUES (
                :prospect_id, :email, :email_hash, :first_name, :last_name, :email_status,
                :title, :seniority, :company, :company_domain, :company_size, :country,
                :industry, :technologies_json, :source_url, :evidence_note,
                :apollo_person_id, :apollo_contact_id, :imported_at, :updated_at
            )
            ON CONFLICT(email) DO UPDATE SET
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                email_status=excluded.email_status,
                title=excluded.title,
                seniority=excluded.seniority,
                company=excluded.company,
                company_domain=excluded.company_domain,
                company_size=excluded.company_size,
                country=excluded.country,
                industry=excluded.industry,
                technologies_json=excluded.technologies_json,
                source_url=excluded.source_url,
                evidence_note=excluded.evidence_note,
                apollo_person_id=excluded.apollo_person_id,
                apollo_contact_id=excluded.apollo_contact_id,
                updated_at=excluded.updated_at
            """,
            values,
        )
        self.connection.commit()
        return prospect_id

    def list_prospects(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM prospects ORDER BY prospect_id").fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["technologies"] = json.loads(item.pop("technologies_json"))
            results.append(item)
        return results

    def get_prospect(self, prospect_id: str) -> Dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM prospects WHERE prospect_id = ?", (prospect_id,)
        ).fetchone()
        if row is None:
            raise KeyError("unknown prospect_id")
        item = dict(row)
        item["technologies"] = json.loads(item.pop("technologies_json"))
        return item

    def suppression_reason(self, email: str) -> Optional[str]:
        row = self.connection.execute(
            "SELECT reason FROM suppressions WHERE email_hash = ?", (email_hash(email),)
        ).fetchone()
        return str(row["reason"]) if row else None

    def suppress(self, email: str, reason: str, evidence_reference: str) -> None:
        allowed = {"unsubscribed", "bounced", "do_not_contact", "customer", "active_opportunity"}
        if reason not in allowed:
            raise ValueError("unsupported suppression reason")
        self.connection.execute(
            """
            INSERT INTO suppressions (email_hash, reason, evidence_reference, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email_hash) DO UPDATE SET
                reason=excluded.reason,
                evidence_reference=excluded.evidence_reference,
                created_at=excluded.created_at
            """,
            (email_hash(email), reason, evidence_reference, utc_now()),
        )
        self.connection.execute(
            "UPDATE prospects SET lifecycle_status = 'suppressed', updated_at = ? WHERE email = ?",
            (utc_now(), email.strip().lower()),
        )
        self.connection.execute(
            """
            UPDATE scores SET qualification_status = 'suppressed',
                blockers_json = ?, scored_at = ?
            WHERE prospect_id = (SELECT prospect_id FROM prospects WHERE email = ?)
            """,
            (
                json.dumps(["suppressed:{0}".format(reason)]),
                utc_now(),
                email.strip().lower(),
            ),
        )
        self.connection.commit()

    def save_score(
        self,
        prospect_id: str,
        campaign_id: str,
        segment_id: str,
        score: int,
        details: Mapping[str, int],
        blockers: Iterable[str],
        warnings: Iterable[str],
        status: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO scores (
                prospect_id, campaign_id, segment_id, score, details_json,
                blockers_json, warnings_json, qualification_status, scored_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(prospect_id, campaign_id) DO UPDATE SET
                segment_id=excluded.segment_id,
                score=excluded.score,
                details_json=excluded.details_json,
                blockers_json=excluded.blockers_json,
                warnings_json=excluded.warnings_json,
                qualification_status=excluded.qualification_status,
                scored_at=excluded.scored_at
            """,
            (
                prospect_id,
                campaign_id,
                segment_id,
                score,
                json.dumps(details, sort_keys=True),
                json.dumps(sorted(set(blockers))),
                json.dumps(sorted(set(warnings))),
                status,
                utc_now(),
            ),
        )
        self.connection.execute(
            "UPDATE prospects SET lifecycle_status = ?, updated_at = ? WHERE prospect_id = ?",
            (status, utc_now(), prospect_id),
        )
        self.connection.commit()

    def qualified_prospects(self, campaign_id: str) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT p.*, s.segment_id, s.score
            FROM prospects p
            JOIN scores s ON s.prospect_id = p.prospect_id
            WHERE s.campaign_id = ? AND s.qualification_status = 'qualified'
              AND p.lifecycle_status = 'qualified'
            ORDER BY s.score DESC, p.prospect_id
            """,
            (campaign_id,),
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["technologies"] = json.loads(item.pop("technologies_json"))
            results.append(item)
        return results

    def save_draft(
        self,
        prospect_id: str,
        campaign_id: str,
        segment_id: str,
        channel: str,
        draft: Mapping[str, Any],
    ) -> str:
        existing = self.connection.execute(
            """
            SELECT draft_id FROM drafts
            WHERE prospect_id = ? AND campaign_id = ? AND channel = ? AND step_index = ?
            """,
            (prospect_id, campaign_id, channel, int(draft["step_index"])),
        ).fetchone()
        if existing:
            return str(existing["draft_id"])
        draft_id = uuid.uuid4().hex
        self.connection.execute(
            """
            INSERT INTO drafts (
                draft_id, prospect_id, campaign_id, segment_id, channel, step_index,
                wait_business_days, subject, body, attributed_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                prospect_id,
                campaign_id,
                segment_id,
                channel,
                int(draft["step_index"]),
                int(draft.get("wait_business_days", 0)),
                str(draft["subject"]),
                str(draft["body"]),
                str(draft["attributed_url"]),
                utc_now(),
            ),
        )
        self.connection.commit()
        return draft_id

    def approve_drafts(
        self, reviewer: str, draft_id: Optional[str] = None, campaign_id: Optional[str] = None
    ) -> int:
        if not reviewer.strip():
            raise ValueError("reviewer is required")
        if draft_id:
            cursor = self.connection.execute(
                """
                UPDATE drafts SET status='approved', approved_by=?, approved_at=?
                WHERE draft_id=? AND status='draft'
                """,
                (reviewer.strip(), utc_now(), draft_id),
            )
        elif campaign_id:
            cursor = self.connection.execute(
                """
                UPDATE drafts SET status='approved', approved_by=?, approved_at=?
                WHERE campaign_id=? AND status='draft'
                """,
                (reviewer.strip(), utc_now(), campaign_id),
            )
        else:
            raise ValueError("draft_id or campaign_id is required")
        self.connection.commit()
        return int(cursor.rowcount)

    def approved_drafts(self, campaign_id: str, channel: str) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT d.*, p.email, p.first_name, p.last_name, p.company, p.title,
                   p.company_domain, p.apollo_contact_id
            FROM drafts d
            JOIN prospects p ON p.prospect_id = d.prospect_id
            LEFT JOIN suppressions x ON x.email_hash = p.email_hash
            WHERE d.campaign_id=? AND d.channel=? AND d.status='approved'
              AND p.lifecycle_status='qualified' AND x.email_hash IS NULL
            ORDER BY p.prospect_id, d.step_index
            """,
            (campaign_id, channel),
        ).fetchall()
        return [dict(row) for row in rows]

    def review_drafts(self, campaign_id: str) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT d.*, p.first_name, p.last_name, p.email, p.title, p.company,
                   p.company_domain, p.source_url, p.evidence_note, s.score
            FROM drafts d
            JOIN prospects p ON p.prospect_id = d.prospect_id
            JOIN scores s ON s.prospect_id = p.prospect_id
                AND s.campaign_id = d.campaign_id
            WHERE d.campaign_id=?
            ORDER BY d.channel, s.score DESC, p.prospect_id, d.step_index
            """,
            (campaign_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_exported(
        self, draft_ids: Iterable[str], campaign_id: str, channel: str, file_name: str
    ) -> str:
        ids = list(draft_ids)
        now = utc_now()
        if ids:
            placeholders = ",".join("?" for _ in ids)
            self.connection.execute(
                "UPDATE drafts SET status='exported', exported_at=? WHERE draft_id IN ({0})".format(
                    placeholders
                ),
                [now] + ids,
            )
        export_id = uuid.uuid4().hex
        self.connection.execute(
            """
            INSERT INTO exports (export_id, campaign_id, channel, file_name, record_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (export_id, campaign_id, channel, file_name, len(ids), now),
        )
        self.connection.commit()
        return export_id

    def record_event(
        self,
        prospect_id: str,
        campaign_id: str,
        event_type: str,
        channel: str,
        evidence_reference: str,
        occurred_at: str,
    ) -> str:
        allowed = {
            "sent",
            "delivered",
            "bounced",
            "unsubscribed",
            "replied",
            "meeting_booked",
            "systems_review_requested",
            "checkout_opened",
            "customer_verified",
        }
        if event_type not in allowed:
            raise ValueError("unsupported event type")
        if not evidence_reference.strip():
            raise ValueError("event evidence_reference is required")
        self.get_prospect(prospect_id)
        event_id = uuid.uuid4().hex
        self.connection.execute(
            """
            INSERT INTO events (
                event_id, prospect_id, campaign_id, event_type, channel,
                evidence_reference, occurred_at, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                prospect_id,
                campaign_id,
                event_type,
                channel,
                evidence_reference,
                occurred_at,
                utc_now(),
            ),
        )
        self.connection.commit()
        return event_id

    def aggregate_counts(self, campaign_id: str) -> Dict[str, Any]:
        def grouped(table: str, column: str) -> Dict[str, int]:
            rows = self.connection.execute(
                "SELECT {0}, COUNT(*) AS total FROM {1} WHERE campaign_id=? GROUP BY {0}".format(
                    column, table
                ),
                (campaign_id,),
            ).fetchall()
            return {str(row[column]): int(row["total"]) for row in rows}

        return {
            "prospects": int(
                self.connection.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
            ),
            "qualification": grouped("scores", "qualification_status"),
            "drafts": grouped("drafts", "status"),
            "events": grouped("events", "event_type"),
            "suppressions": int(
                self.connection.execute("SELECT COUNT(*) FROM suppressions").fetchone()[0]
            ),
            "exports": int(
                self.connection.execute(
                    "SELECT COUNT(*) FROM exports WHERE campaign_id=?", (campaign_id,)
                ).fetchone()[0]
            ),
        }
