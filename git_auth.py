"""
Forge-neutral git authentication and credential redaction.

Credentials never go into a remote URL (git writes it to ``.git/config``):
each git call gets the forge's ``Authorization`` header through its own
process environment as ``http.<forge url>.extraHeader``, so git sends it to no
other host. The header value is built by the forge client (``*_client.py``)
and passed in.
"""

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager

import git

logger = logging.getLogger(__name__)

_USERINFO_RE = re.compile(r"(?<=://)[^/@\s]+@")


def env(url: str, header: str) -> dict[str, str]:
    """Environment for one git call that sends *header* as ``http.<url>.extraHeader``, only to *url*."""
    # Overrides any inherited GIT_CONFIG_COUNT/KEY_0/VALUE_0 for this one call.
    return {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"http.{url}.extraHeader", "GIT_CONFIG_VALUE_0": header}


def redact(text: str, *secrets: str) -> str:
    """Mask ``scheme://user:pass@`` userinfo and every non-empty secret in *text*, longest first."""
    text = _USERINFO_RE.sub("***@", text)
    for secret in sorted(filter(None, secrets), key=len, reverse=True):
        text = text.replace(secret, "***")
    return text


@contextmanager
def redacted(*secrets: str) -> Iterator[None]:
    """Re-raise a git command error as ``RuntimeError`` with credentials masked."""
    try:
        yield
    except git.GitCommandError as exc:
        # from None: the original exception's text is the unmasked one.
        raise RuntimeError(redact(str(exc), *secrets)) from None
