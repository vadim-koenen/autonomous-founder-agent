import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from founder_agent.preflight import PreflightInputError, analyze_preflight
from founder_agent.preflight_github import (
    parse_github_repository_url,
    preflight_github_repository,
)


NOW = datetime(2026, 7, 11, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def ready_payload():
    return {
        "repository": {
            "url": "https://github.com/example/agent-server",
            "description": "A bounded MCP server that returns verified build metadata.",
            "archived": False,
            "pushed_at": "2026-07-10T12:00:00Z",
            "license_spdx": "MIT",
        },
        "registry": {
            "name": "io.example/agent-server",
            "description": "Verified build metadata for agent workflows.",
            "version": "1.2.3",
            "remotes": [
                {
                    "type": "streamable-http",
                    "url": "https://agent.example.com/mcp",
                }
            ],
            "packages": [],
        },
        "files": ["README.md", "LICENSE", "SECURITY.md", "pyproject.toml"],
    }


class PreflightTest(unittest.TestCase):
    def test_ready_report_is_deterministic_and_never_executes_target(self):
        first = analyze_preflight(ready_payload(), observed_at=NOW)
        second = analyze_preflight(ready_payload(), observed_at=NOW)

        self.assertEqual(first["report_id"], second["report_id"])
        self.assertEqual(100.0, first["score"])
        self.assertEqual("ready_for_live_protocol_test", first["verdict"])
        self.assertFalse(first["execution_claims"]["target_code_executed"])
        self.assertFalse(first["execution_claims"]["security_audit_completed"])
        self.assertIn("does not execute target code", " ".join(first["limitations"]))

    def test_missing_public_assurance_produces_actions_not_false_safety(self):
        payload = ready_payload()
        payload["repository"].update(
            {
                "description": "",
                "archived": True,
                "pushed_at": "2024-01-01T00:00:00Z",
                "license_spdx": "",
            }
        )
        payload["registry"] = {}
        payload["files"] = []

        report = analyze_preflight(payload, observed_at=NOW)

        self.assertEqual("insufficient_public_assurance", report["verdict"])
        self.assertIn("repository_active", report["risk_flags"])
        self.assertIn("license_declared", report["risk_flags"])
        self.assertGreaterEqual(len(report["next_actions"]), 5)

    def test_github_adapter_is_allowlisted_and_does_not_persist_token(self):
        calls = []

        def transport(url, token):
            calls.append((url, token))
            if url.endswith("/contents"):
                return [
                    {"type": "file", "path": "README.md"},
                    {"type": "file", "path": "SECURITY.md"},
                    {"type": "file", "path": "LICENSE"},
                ]
            return {
                "description": "A public MCP integration server for GitHub workflows.",
                "archived": False,
                "fork": False,
                "pushed_at": "2026-07-11T11:00:00Z",
                "default_branch": "main",
                "license": {"spdx_id": "MIT"},
                "open_issues_count": 4,
                "stargazers_count": 100,
            }

        report = preflight_github_repository(
            "https://github.com/example/mcp-server",
            github_token="runtime-only-token",
            transport=transport,
            observed_at=NOW,
        )

        self.assertEqual(2, len(calls))
        self.assertTrue(all(url.startswith("https://api.github.com/repos/example/mcp-server") for url, _ in calls))
        self.assertTrue(all(token == "runtime-only-token" for _, token in calls))
        self.assertNotIn("runtime-only-token", json.dumps(report))

    def test_repository_parser_rejects_ssrf_and_extra_paths(self):
        self.assertEqual(
            ("modelcontextprotocol", "inspector"),
            parse_github_repository_url("https://github.com/modelcontextprotocol/inspector.git"),
        )
        for url in (
            "http://github.com/example/repo",
            "https://github.com.evil.test/example/repo",
            "https://github.com/example/repo/issues/1",
            "https://127.0.0.1/example/repo",
        ):
            with self.assertRaises(PreflightInputError):
                parse_github_repository_url(url)

    def test_dual_rail_contract_is_truthful_while_payments_are_pending(self):
        product = json.loads(
            (ROOT / "products" / "mcp-agent-preflight" / "product.json").read_text(
                encoding="utf-8"
            )
        )
        contract = json.loads(
            (ROOT / "products" / "mcp-agent-preflight" / "openapi.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertFalse(product["execution_claims"]["paid_endpoint_live"])
        self.assertFalse(product["execution_claims"]["wallet_connected"])
        self.assertIsNone(product["x402"]["pay_to"])
        self.assertEqual(
            "contract_only_runtime_host_and_wallet_pending",
            contract["x-deployment-status"],
        )
        metered_route = contract["paths"]["/v1/preflight/full"]["post"]
        self.assertFalse(metered_route["x-target-code-executed"])
        self.assertIn("402", metered_route["responses"])

    def test_public_demo_is_functional_and_never_requests_secrets(self):
        page = (ROOT / "site" / "preflight.html").read_text(encoding="utf-8")

        self.assertIn("https://api.github.com/repos/", page)
        self.assertIn("Run preflight", page)
        self.assertIn("Request metered route", page)
        self.assertIn("target_code_executed: false", page)
        self.assertIn("wallet</span><strong class=\"truth-value\">Not connected", page)
        self.assertNotIn("private key", page.lower())
        self.assertNotIn("localStorage", page)
        self.assertRegex(
            page,
            r"\.button\.secondary:hover, \.button\.secondary:focus-visible \{[^}]*background: var\(--teal\);[^}]*color: #ffffff;",
        )

    def test_bundled_sample_is_explicitly_synthetic(self):
        sample_input = json.loads(
            (ROOT / "products" / "mcp-agent-preflight" / "sample-input.json").read_text(
                encoding="utf-8"
            )
        )
        sample_response = json.loads(
            (ROOT / "products" / "mcp-agent-preflight" / "sample-response.json").read_text(
                encoding="utf-8"
            )
        )

        expected = "synthetic_fixture_not_market_evidence"
        self.assertEqual(expected, sample_input["sample_status"])
        self.assertEqual(expected, sample_response["sample_status"])


if __name__ == "__main__":
    unittest.main()
