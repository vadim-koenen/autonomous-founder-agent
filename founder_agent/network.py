"""TLS helpers for fixed, allowlisted HTTPS clients."""

from __future__ import annotations

import os
import ssl
from pathlib import Path


def verified_tls_context() -> ssl.SSLContext:
    """Use the configured/default CA bundle, including the standard macOS fallback."""

    candidates = [
        os.environ.get("SSL_CERT_FILE", ""),
        ssl.get_default_verify_paths().cafile or "",
        "/etc/ssl/cert.pem",
    ]
    cafile = next((item for item in candidates if item and Path(item).is_file()), None)
    return ssl.create_default_context(cafile=cafile)
