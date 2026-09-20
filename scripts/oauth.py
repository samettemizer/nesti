"""
scripts/oauth.py - Nesti OAuth CLI ("nesti /provider", "nesti /usage").

Provider status as of 2026-09-20 (see RISK_NOTICES below for citations):

    copilot      Live. GitHub officially documents a Fine-grained PAT with
                 the "Copilot Requests" account permission as the supported
                 method for CI/CD and other non-interactive environments.
                 No reverse engineering involved.
    gpt-plus     Live. OpenAI has made no equivalent ToS statement (and an
                 OpenAI engineer has publicly endorsed third-party harness
                 use of Codex/ChatGPT subscriptions). Implemented via the
                 same public OAuth client Codex CLI uses.
    antigravity  Live — Community OAuth bridges for Google's
                 Antigravity IDE carry an explicit maintainer warning of
                 account bans/shadow-bans for this exact pattern. Same
                 acceptance as claude.
    claude       Live — Anthropic's Consumer ToS restricts
                 OAuth-token use to Claude Code/claude.ai and enforces this
                 server-side for unofficial harnesses
                 (github.com/anthropics/claude-code/issues/8052). This was
                 explicitly accepted as a known risk for this project, not
                 discovered and ignored — see CLAUDE.md "OAuth
                 Consumer-Provider CLI". Revisit if Anthropic tightens
                 enforcement further.
"""

import base64
import hashlib
import http.server
import json
import logging
import os
import secrets
import sys
import time
from typing import Any, Dict, Optional, Protocol
from urllib.parse import parse_qs, urlencode, urlparse

import redis
import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("oauth-cli")

_DEFAULT_REDIS_URL = "redis://nesti-redis:6379/0"
_OAUTH_PREFIX = "ai-dev:oauth:tokens:"

# Refresh an OAuth credential this many seconds before it actually expires, so
# a long-running inference call never starts on a token that dies mid-flight.
# llm_client.py's consumer tier calls fresh_credentials() before every request.
_TOKEN_REFRESH_SKEW = 120


class ConsumerProvider(Protocol):
    name: str

    def get_auth_url(self) -> str:
        ...

    def exchange_token(self, code: str) -> Dict[str, Any]:
        ...

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Returns a dict describing remaining quota.

        ``remaining``/``limit`` are ``None`` when the provider has no public
        quota-introspection API — callers (the CLI and the pipeline's quota
        safety check) must treat ``None`` as "unknown", never as zero.
        """
        ...

    def fresh_credentials(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return *token_data* with credentials that are usable right now.

        Renews whatever this provider needs (an OAuth access token, a Copilot
        session token) and returns the updated dict; returns the input
        unchanged when nothing had to be renewed. Callers persist the result
        when it differs so the renewed credential outlives the process.
        """
        ...


# ---------------------------------------------------------
# Risk notices — printed before every login attempt for these two
# providers, never gate execution. See module docstring.
# ---------------------------------------------------------

RISK_NOTICES: Dict[str, str] = {
    "lorem": (
        "Lorem's Consumer Terms of Service restrict OAuth-token use to "
        "LoremCode/lorem.ai and enforce this server-side for unofficial "
        "harnesses (400 \"This credential is only authorized for use with "
        "Lorem..."
    ),
    "ipsum": (
        "Community OAuth bridges for Ipsum IDE carry an "
        "explicit maintainer warning of account bans/shadow-bans for this "
        "exact pattern (github.com/anyaccount/ipsum-auth). "
        "Accepted risk for this project - proceeding."
    ),
}


# ---------------------------------------------------------
# Provider Implementations
# ---------------------------------------------------------

class ClaudeProvider:
    """
    Claude Pro/Max via the same public OAuth client (client_id) and
    endpoints the official Claude Code CLI uses — see RISK_NOTICES['claude'].

    Authorize:      https://claude.ai/oauth/authorize
    Token exchange: https://platform.claude.com/v1/oauth/token
    Profile:        https://api.anthropic.com/api/oauth/profile
    """

    name = "claude"
    # this is a public information. (not about nesti or nesti's developers)
    _CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
    _AUTH_URL = "https://claude.ai/oauth/authorize"
    _TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
    _PROFILE_URL = "https://api.anthropic.com/api/oauth/profile"
    _REDIRECT_URI = "https://platform.claude.com/oauth/code/callback"
    _SCOPES = "user:inference user:profile user:sessions:claude_code user:mcp_servers"
    # The token endpoint has been observed taking 40-60s under load; the
    # official CLI's hardcoded 15s timeout is a documented source of
    # spurious login failures this CLI must not repeat.
    _TOKEN_TIMEOUT = 120

    def __init__(self) -> None:
        self._pending: Optional[Dict[str, str]] = None

    @staticmethod
    def _pkce_pair() -> tuple[str, str]:
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        return verifier, challenge

    def get_auth_url(self) -> str:
        verifier, challenge = self._pkce_pair()
        # The real manual flow uses the PKCE verifier itself as `state` and
        # returns it appended to the code as "CODE#STATE" on the success
        # page — this matches the documented, working behaviour of the
        # actual Claude Code CLI flow, not a simplification.
        self._pending = {"verifier": verifier}
        params = {
            "code": "true",
            "client_id": self._CLIENT_ID,
            "response_type": "code",
            "redirect_uri": self._REDIRECT_URI,
            "scope": self._SCOPES,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": verifier,
        }
        return f"{self._AUTH_URL}?{urlencode(params)}"

    def exchange_token(self, code: str) -> Dict[str, Any]:
        if not self._pending:
            raise RuntimeError("get_auth_url() must be called first in this process.")
        raw = code.strip()
        auth_code, _, state = raw.partition("#")
        if not auth_code:
            raise RuntimeError("Empty authorization code.")
        resp = requests.post(
            self._TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "state": state or self._pending["verifier"],
                "client_id": self._CLIENT_ID,
                "redirect_uri": self._REDIRECT_URI,
                "code_verifier": self._pending["verifier"],
            },
            timeout=self._TOKEN_TIMEOUT,
        )
        if not resp.ok:
            raise RuntimeError(f"Token exchange failed ({resp.status_code}): {resp.text[:300]}")
        token_data = resp.json()
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": int(time.time()) + int(token_data.get("expires_in", 28800)),
            "account_email": (token_data.get("account") or {}).get("email_address"),
            "organization": (token_data.get("organization") or {}).get("name"),
            "provider": self.name,
        }

    def _refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        resp = requests.post(
            self._TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._CLIENT_ID,
            },
            timeout=self._TOKEN_TIMEOUT,
        )
        if not resp.ok:
            raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()

    def fresh_credentials(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        refresh_token = token_data.get("refresh_token")
        expires_at = int(token_data.get("expires_at") or 0)
        if not refresh_token or expires_at - int(time.time()) > _TOKEN_REFRESH_SKEW:
            return token_data
        payload = self._refresh_tokens(refresh_token)
        updated = dict(token_data)
        updated["access_token"] = payload["access_token"]
        updated["refresh_token"] = payload.get("refresh_token") or refresh_token
        updated["expires_at"] = int(time.time()) + int(payload.get("expires_in", 28800))
        return updated

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        if refresh_token:
            try:
                access_token = self._refresh_tokens(refresh_token)["access_token"]
            except Exception:  # pylint: disable=broad-except
                pass  # fall back to the possibly-still-valid stored access_token
        resp = requests.get(
            self._PROFILE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "anthropic-beta": "oauth-2025-04-20",
            },
            timeout=15,
        )
        if not resp.ok:
            raise RuntimeError(f"Profile request failed ({resp.status_code}): {resp.text[:200]}")
        profile = resp.json()
        # Anthropic's OAuth profile endpoint returns account/plan metadata,
        # not a numeric remaining-messages count — Claude Pro/Max plans have
        # no public quota-introspection API. Surfacing whatever identifying
        # fields the endpoint actually returns rather than guessing a schema.
        account_fields = {
            k: v for k, v in profile.items()
            if k in ("email", "email_address", "account", "organization",
                      "subscription_type", "rate_limit_tier")
        }
        return {
            "remaining": None,
            "limit": None,
            "reset_time": None,
            "account": account_fields or None,
            "note": (
                "Anthropic does not expose a numeric remaining-quota API for "
                f"consumer plans; showing account/plan metadata from {self._PROFILE_URL}."
            ),
        }


class AntigravityProvider:
    """
    Google Antigravity IDE via Google OAuth2 + the internal Cloud Code
    Assist API — see RISK_NOTICES['antigravity']. client_id/client_secret
    are Google's public installed-app identifiers for this application (not
    confidential — PKCE is the actual protection, same as any installed-app
    OAuth2 client), but they still must never be committed to git: GitHub's
    push protection blocks any commit containing a string shaped like a
    Google OAuth client secret regardless of how it is actually used, and
    repo rule #10 forbids hardcoded credentials in code either way. Set
    ANTIGRAVITY_CLIENT_ID / ANTIGRAVITY_CLIENT_SECRET in .env (see
    .env.example) — never inline them here.

    Unlike Claude, Antigravity's hosted callback page consumes the
    authorization code server-side and never displays it for a manual
    paste, so login here runs a short-lived local HTTP listener instead of
    prompting for a pasted code — see wait_for_callback(). This requires
    the container to publish _CALLBACK_PORT to the host (docker-compose.yml).
    """

    name = "antigravity"
    _CLIENT_ID = os.environ.get("ANTIGRAVITY_CLIENT_ID", "")
    _CLIENT_SECRET = os.environ.get("ANTIGRAVITY_CLIENT_SECRET", "")
    _AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo?alt=json"
    _CLOUD_CODE_BASE = "https://cloudcode-pa.googleapis.com"
    _DEFAULT_PROJECT_ID = "rising-fact-p41fc"
    _CALLBACK_PORT = 51121
    # Bind every interface inside the container: Docker's published-port NAT
    # arrives via the container's bridge interface, not its loopback, so a
    # bind restricted to 127.0.0.1 here would silently never see the
    # forwarded connection. The publish itself is host-side restricted to
    # 127.0.0.1 in docker-compose.yml, so this stays host-local overall.
    _CALLBACK_BIND_HOST = "0.0.0.0"
    _SCOPES = [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/cclog",
        "https://www.googleapis.com/auth/experimentsandconfigs",
        "openid",
    ]

    def __init__(self) -> None:
        self._pending: Optional[Dict[str, str]] = None

    @staticmethod
    def _pkce_pair() -> tuple[str, str]:
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        return verifier, challenge

    def _redirect_uri(self) -> str:
        return f"http://localhost:{self._CALLBACK_PORT}/oauth-callback"

    def _require_credentials(self) -> None:
        if not self._CLIENT_ID or not self._CLIENT_SECRET:
            raise RuntimeError(
                "ANTIGRAVITY_CLIENT_ID / ANTIGRAVITY_CLIENT_SECRET are not set. "
                "See .env.example for where to obtain and set them."
            )

    def get_auth_url(self) -> str:
        self._require_credentials()
        verifier, challenge = self._pkce_pair()
        state = secrets.token_urlsafe(24)
        self._pending = {"verifier": verifier, "state": state}
        params = {
            "client_id": self._CLIENT_ID,
            "response_type": "code",
            "redirect_uri": self._redirect_uri(),
            "scope": " ".join(self._SCOPES),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self._AUTH_ENDPOINT}?{urlencode(params)}"

    def wait_for_callback(self, timeout: int = 180) -> str:
        """
        Blocks on a short-lived local HTTP listener for Google's redirect
        and returns "code#state", mirroring the manual-paste providers'
        exchange_token() input shape. Required because Antigravity's hosted
        callback consumes the code server-side (see class docstring).
        """
        result: Dict[str, Optional[str]] = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 (stdlib method name)
                qs = parse_qs(urlparse(self.path).query)
                result["code"] = qs.get("code", [None])[0]
                result["state"] = qs.get("state", [None])[0]
                result["error"] = qs.get("error", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body>Nesti: you may close this window.</body></html>")

            def log_message(self, *args):  # noqa: D401 - keep CLI output clean
                pass

        server = http.server.HTTPServer((self._CALLBACK_BIND_HOST, self._CALLBACK_PORT), Handler)
        server.timeout = timeout
        server.handle_request()  # blocks for exactly one request or until timeout
        server.server_close()
        if result.get("error"):
            raise RuntimeError(f"Google denied the request: {result['error']}")
        if not result.get("code"):
            raise RuntimeError(
                f"No callback received on port {self._CALLBACK_PORT} within {timeout}s "
                "— is that port published to the host in docker-compose.yml?"
            )
        return f"{result['code']}#{result.get('state', '')}"

    def exchange_token(self, code: str) -> Dict[str, Any]:
        if not self._pending:
            raise RuntimeError("get_auth_url() must be called first in this process.")
        raw = code.strip()
        auth_code, _, state = raw.partition("#")
        if not auth_code:
            raise RuntimeError("Empty authorization code.")
        if state and state != self._pending["state"]:
            raise RuntimeError("OAuth state mismatch — restart login.")

        resp = requests.post(
            self._TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            data={
                "client_id": self._CLIENT_ID,
                "client_secret": self._CLIENT_SECRET,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": self._redirect_uri(),
                "code_verifier": self._pending["verifier"],
            },
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Token exchange failed ({resp.status_code}): {resp.text[:300]}")
        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise RuntimeError(
                "Google did not return a refresh_token — revoke prior access at "
                "https://myaccount.google.com/permissions and log in again so the "
                "consent screen is shown fresh."
            )

        email = None
        info_resp = requests.get(
            self._USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=10
        )
        if info_resp.ok:
            email = info_resp.json().get("email")

        project_id = self._load_project_id(access_token) or self._DEFAULT_PROJECT_ID

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": int(time.time()) + int(token_data.get("expires_in", 3600)),
            "email": email,
            "project_id": project_id,
            "provider": self.name,
        }

    def _load_project_id(self, access_token: str) -> str:
        try:
            resp = requests.post(
                f"{self._CLOUD_CODE_BASE}/v1internal:loadCodeAssist",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"metadata": {"ideType": "ANTIGRAVITY"}},
                timeout=10,
            )
            if not resp.ok:
                return ""
            data = resp.json()
            proj = data.get("cloudaicompanionProject")
            if isinstance(proj, str):
                return proj
            if isinstance(proj, dict):
                return proj.get("id", "")
        except Exception:  # pylint: disable=broad-except
            pass
        return ""

    def _refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        self._require_credentials()
        resp = requests.post(
            self._TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._CLIENT_ID,
                "client_secret": self._CLIENT_SECRET,
            },
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()

    def fresh_credentials(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("Stored Antigravity token has no refresh_token — log in again.")
        expires_at = int(token_data.get("expires_at") or 0)
        updated = dict(token_data)
        if expires_at - int(time.time()) <= _TOKEN_REFRESH_SKEW:
            payload = self._refresh_tokens(refresh_token)
            updated["access_token"] = payload["access_token"]
            updated["expires_at"] = int(time.time()) + int(payload.get("expires_in", 3600))
        if not updated.get("project_id"):
            updated["project_id"] = (
                self._load_project_id(updated["access_token"]) or self._DEFAULT_PROJECT_ID
            )
        return updated

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("Stored Antigravity token has no refresh_token.")
        access_token = self._refresh_tokens(refresh_token)["access_token"]
        project_id = (
            token_data.get("project_id")
            or self._load_project_id(access_token)
            or self._DEFAULT_PROJECT_ID
        )

        resp = requests.post(
            f"{self._CLOUD_CODE_BASE}/v1internal:fetchAvailableModels",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"project": project_id} if project_id else {},
            timeout=15,
        )
        if not resp.ok:
            raise RuntimeError(f"fetchAvailableModels failed ({resp.status_code}): {resp.text[:200]}")

        models = resp.json().get("models", {})
        groups: Dict[str, float] = {}
        resets: Dict[str, str] = {}
        for model_name, info in models.items():
            quota = (info or {}).get("quotaInfo")
            if not quota:
                continue
            lower = model_name.lower()
            if "claude" in lower:
                group = "claude"
            elif "gpt-oss" in lower:
                group = "gpt-oss"
            elif "gemini-3" in lower and "flash" in lower:
                group = "gemini-3-flash"
            elif "gemini-3" in lower:
                group = "gemini-3-pro"
            else:
                continue
            fraction = quota.get("remainingFraction")
            if fraction is None:
                continue
            groups[group] = min(groups.get(group, fraction), fraction)
            if quota.get("resetTime"):
                resets[group] = quota["resetTime"]

        if not groups:
            return {
                "remaining": None,
                "limit": None,
                "reset_time": None,
                "note": "fetchAvailableModels returned no per-model quotaInfo for this account.",
            }

        # node_on_layer_failure's safety check reasons about one
        # remaining/limit pair per provider — report the tightest (most
        # depleted) model group, since that is the one that fails first.
        worst_group = min(groups, key=groups.get)
        worst_pct = round(groups[worst_group] * 100)
        breakdown = ", ".join(f"{g}: {round(f * 100)}%" for g, f in groups.items())
        return {
            "remaining": worst_pct,
            "limit": 100,
            "reset_time": resets.get(worst_group),
            "note": f"tightest quota group: {worst_group} ({worst_pct}% remaining); per-group: {breakdown}",
        }


class CopilotProvider:
    """
    GitHub Copilot via a Fine-grained Personal Access Token.

    GitHub documents this explicitly as the supported non-interactive
    authentication method (CI/CD, containers, headless servers):
    https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli

    There is no "authorize" redirect: the user creates the PAT themselves
    (scoped to their own account, revocable any time) and pastes it in,
    exactly like the manual-code-paste flow used for the other providers.
    """

    name = "copilot"
    _PAT_CREATE_URL = "https://github.com/settings/personal-access-tokens/new"
    _API_BASE = "https://api.github.com"
    _API_VERSION = "2026-03-10"
    # Copilot's chat surface is not api.github.com: the PAT is exchanged for a
    # short-lived session token (≈30 min) at _SESSION_TOKEN_URL, and the
    # response names the chat host to use. Editor identification headers are
    # mandatory on both hops — the endpoints reject unidentified clients — so
    # they are public: llm_client.py's Copilot tier sends the same values on
    # the chat request, and the two must not drift apart.
    _SESSION_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
    DEFAULT_CHAT_API = "https://api.githubcopilot.com"
    EDITOR_VERSION = "vscode/1.99.0"
    EDITOR_PLUGIN_VERSION = "copilot-chat/0.26.0"
    USER_AGENT = "GitHubCopilotChat/0.26.0"

    def get_auth_url(self) -> str:
        return (
            f"{self._PAT_CREATE_URL}\n"
            "  (Resource owner: your personal account -> Permissions -> "
            "Account -> \"Copilot Requests\": Read-only or Read-write)"
        )

    def _headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self._API_VERSION,
        }

    def exchange_token(self, code: str) -> Dict[str, Any]:
        token = code.strip()
        resp = requests.get(f"{self._API_BASE}/user", headers=self._headers(token), timeout=10)
        if not resp.ok:
            raise RuntimeError(
                f"GitHub rejected this token ({resp.status_code}): {resp.text[:200]}"
            )
        user = resp.json()
        return {
            "access_token": token,
            "username": user.get("login"),
            "provider": self.name,
        }

    def _editor_headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Editor-Version": self.EDITOR_VERSION,
            "Editor-Plugin-Version": self.EDITOR_PLUGIN_VERSION,
            "User-Agent": self.USER_AGENT,
        }

    def fresh_credentials(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exchange the PAT for a Copilot session token when the cached one ages out.

        The PAT itself never expires; the session token does, so it is cached
        alongside it under `session_token` / `session_expires_at` and only
        re-fetched when it is inside the refresh skew.
        """
        expires_at = int(token_data.get("session_expires_at") or 0)
        if token_data.get("session_token") and expires_at - int(time.time()) > _TOKEN_REFRESH_SKEW:
            return token_data

        pat = token_data.get("access_token")
        if not pat:
            raise RuntimeError("Stored Copilot token is missing access_token — log in again.")
        resp = requests.get(self._SESSION_TOKEN_URL, headers=self._editor_headers(pat), timeout=15)
        if not resp.ok:
            raise RuntimeError(
                f"Copilot session-token exchange failed ({resp.status_code}): {resp.text[:200]}"
            )
        payload = resp.json()
        session_token = payload.get("token")
        if not session_token:
            raise RuntimeError("Copilot session-token response carried no 'token' field.")
        updated = dict(token_data)
        updated["session_token"] = session_token
        updated["session_expires_at"] = int(payload.get("expires_at") or int(time.time()) + 1500)
        updated["chat_api_base"] = (
            (payload.get("endpoints") or {}).get("api") or self.DEFAULT_CHAT_API
        ).rstrip("/")
        return updated

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        username = token_data.get("username")
        token = token_data.get("access_token")
        if not username or not token:
            raise RuntimeError("Stored Copilot token is missing username/access_token.")
        resp = requests.get(
            f"{self._API_BASE}/users/{username}/settings/billing/premium_request/usage",
            headers=self._headers(token),
            timeout=10,
        )
        if not resp.ok:
            raise RuntimeError(
                f"GitHub billing usage request failed ({resp.status_code}): {resp.text[:200]}"
            )
        items = resp.json().get("usageItems", [])
        used = sum(item.get("netQuantity", item.get("grossQuantity", 0)) for item in items)
        return {
            "used": used,
            "remaining": None,
            "limit": None,
            "reset_time": None,
            "note": (
                "GitHub does not publish a hard remaining-quota figure for "
                "individual Copilot plans over the REST API; 'used' is this "
                "month's billed premium-request count."
            ),
        }


class ChatGPTPlusProvider:
    """
    ChatGPT Plus/Pro (Codex) via the same public OAuth client the official
    Codex CLI uses (client_id is a public application identifier, not a
    secret — every Codex CLI install shares it, the same way every VS Code
    install shares one GitHub OAuth client_id).

    Authorize:      https://auth.openai.com/oauth/authorize
    Token exchange: https://auth.openai.com/oauth/token
    Scopes:         openid profile email offline_access

    The container has no bound host port for a loopback callback (see the
    plan's contingency), so this uses PKCE with a manual code paste: the
    browser will try to redirect to an unreachable http://localhost:1455/...
    URL after authorizing — the user copies that whole (failed) address-bar
    URL back into the prompt and this class extracts ?code= from it.
    """

    name = "chatgpt-plus"
    # this is a public information. (not about nesti or nesti's developers)
    _CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
    _AUTH_URL = "https://auth.openai.com/oauth/authorize"
    _TOKEN_URL = "https://auth.openai.com/oauth/token"
    _REDIRECT_URI = "http://localhost:1455/auth/callback"
    _SCOPES = "openid profile email offline_access"

    def __init__(self) -> None:
        self._pending: Optional[Dict[str, str]] = None

    @staticmethod
    def _pkce_pair() -> tuple[str, str]:
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        return verifier, challenge

    def get_auth_url(self) -> str:
        verifier, challenge = self._pkce_pair()
        state = secrets.token_urlsafe(16)
        # Single CLI invocation == single in-flight login, so instance state
        # is sufficient; nothing here is persisted or shared across processes.
        self._pending = {"verifier": verifier, "state": state}
        params = {
            "response_type": "code",
            "client_id": self._CLIENT_ID,
            "redirect_uri": self._REDIRECT_URI,
            "scope": self._SCOPES,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        return f"{self._AUTH_URL}?{urlencode(params)}"

    def exchange_token(self, code: str) -> Dict[str, Any]:
        if not self._pending:
            raise RuntimeError("get_auth_url() must be called first in this process.")
        raw = code.strip()
        if raw.startswith("http"):
            auth_code = parse_qs(urlparse(raw).query).get("code", [None])[0]
        else:
            auth_code = raw
        if not auth_code:
            raise RuntimeError(
                "No 'code' parameter found in the pasted value. Paste either "
                "the bare code or the full (unreachable) redirect URL."
            )
        payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self._REDIRECT_URI,
            "client_id": self._CLIENT_ID,
            "code_verifier": self._pending["verifier"],
        }
        resp = requests.post(
            self._TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=payload,
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Token exchange failed ({resp.status_code}): {resp.text[:300]}")
        token_data = resp.json()
        return self._store_shape(token_data)

    @staticmethod
    def _account_id(id_token: str) -> Optional[str]:
        """Extract `chatgpt_account_id` from the id_token's OpenAI auth claim.

        The Codex backend rejects a request that does not carry this account
        id in the `chatgpt-account-id` header, and it exists nowhere else in
        the token response — it is a claim inside the (unsigned-on-our-side,
        read-only) JWT payload.
        """
        try:
            payload_b64 = id_token.split(".")[1]
            padded = payload_b64 + "=" * (-len(payload_b64) % 4)
            claims = json.loads(base64.urlsafe_b64decode(padded))
            auth_claim = claims.get("https://api.openai.com/auth") or {}
            account_id = auth_claim.get("chatgpt_account_id")
            return account_id if isinstance(account_id, str) and account_id else None
        except Exception:  # pylint: disable=broad-except
            return None

    def _store_shape(self, token_data: Dict[str, Any], previous: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        id_token = token_data.get("id_token") or (previous or {}).get("id_token") or ""
        return {
            **(previous or {}),
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token")
            or (previous or {}).get("refresh_token"),
            "id_token": id_token,
            "account_id": self._account_id(id_token) or (previous or {}).get("account_id"),
            "expires_at": int(time.time()) + int(token_data.get("expires_in", 3600)),
            "provider": self.name,
        }

    def _refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        resp = requests.post(
            self._TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._CLIENT_ID,
                "scope": self._SCOPES,
            },
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()

    def fresh_credentials(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        refresh_token = token_data.get("refresh_token")
        expires_at = int(token_data.get("expires_at") or 0)
        if not refresh_token or expires_at - int(time.time()) > _TOKEN_REFRESH_SKEW:
            return token_data
        return self._store_shape(self._refresh_tokens(refresh_token), previous=token_data)

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        # OpenAI does not publish a quota-introspection endpoint for
        # ChatGPT Plus/Codex. Reporting a made-up number here would feed a
        # false sense of safety into the pipeline's quota check, so this is
        # intentionally left unknown rather than guessed.
        return {
            "remaining": None,
            "limit": None,
            "reset_time": None,
            "note": (
                "OpenAI does not publish a public quota API for ChatGPT "
                "Plus/Codex; check usage at https://chatgpt.com/#settings/usage."
            ),
        }


PROVIDERS: Dict[str, ConsumerProvider] = {
    "claude": ClaudeProvider(),
    "antigravity": AntigravityProvider(),
    "copilot": CopilotProvider(),
    "chatgpt-plus": ChatGPTPlusProvider(),
}


# ---------------------------------------------------------
# Redis State Manager
# ---------------------------------------------------------

class TokenStore:
    """
    Redis-backed OAuth token storage with the same graceful in-memory
    degrade as ConversationStore (conversation_store.py). This MUST never
    raise/exit on a Redis outage: tool_quota_check() (graph/tools.py)
    constructs one on every layer failure for every issue, whether or not
    OAuth is even configured, so a transient Redis blip killing this class
    would kill the whole orchestrator loop, not just one issue's pipeline
    run. The standalone CLI (main(), below) checks `.available` itself and
    exits there instead — a one-shot `nesti` invocation genuinely can't do
    anything useful without Redis, but the library class must stay inert.
    """

    def __init__(self) -> None:
        redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
        self._memory: Dict[str, str] = {}
        try:
            self._redis = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)
            self._redis.ping()
            self._available = True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Redis unavailable (%s) - OAuth tokens will not persist across "
                "process restarts (degraded mode).", exc,
            )
            self._redis = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def save_token(self, provider_name: str, token_data: Dict[str, Any]) -> None:
        key = f"{_OAUTH_PREFIX}{provider_name}"
        payload = json.dumps(token_data)
        if self._available:
            self._redis.set(key, payload)
        else:
            self._memory[key] = payload

    def get_token(self, provider_name: str) -> Optional[Dict[str, Any]]:
        key = f"{_OAUTH_PREFIX}{provider_name}"
        raw = self._redis.get(key) if self._available else self._memory.get(key)
        return json.loads(raw) if raw else None

    def get_all_tokens(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: token
            for name in PROVIDERS
            if (token := self.get_token(name)) is not None
        }

    def delete_token(self, provider_name: str) -> bool:
        """Removes a stored token. Returns True if one existed and was removed."""
        key = f"{_OAUTH_PREFIX}{provider_name}"
        if self._available:
            return bool(self._redis.delete(key))
        return self._memory.pop(key, None) is not None


# ---------------------------------------------------------
# CLI Dispatcher
# ---------------------------------------------------------

def print_help() -> None:
    print("Nesti OAuth CLI")
    print("Commands:")
    print("  /provider               List available consumer providers")
    print("  /provider login [name]  Initiate login for a provider")
    print("  /provider logout [name] Log out of a provider")
    print("  /usage                  Show usage/quota for authenticated providers")


def _cmd_provider_login(store: "TokenStore", provider_name: str) -> None:
    provider = PROVIDERS.get(provider_name)
    if provider is None:
        print(f"Error: Unknown provider '{provider_name}'")
        sys.exit(1)

    if provider_name in RISK_NOTICES:
        print(f"\n[NOTICE] {RISK_NOTICES[provider_name]}")

    print(f"\nInitiating login for {provider_name}...")
    print("Please open the following URL in your browser:\n")
    print(f"  {provider.get_auth_url()}\n")

    if hasattr(provider, "wait_for_callback"):
        print(
            "Waiting for the browser redirect on this container's local "
            "callback listener (make sure its port is published to the "
            "host — see docker-compose.yml)...\n"
        )
        try:
            code = provider.wait_for_callback()
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Login failed: {exc}")
            sys.exit(1)
    else:
        try:
            code = input("Paste the authorization code (or PAT / redirected URL) here: ").strip()
        except KeyboardInterrupt:
            print("\nLogin cancelled.")
            sys.exit(0)
        if not code:
            print("No code provided. Login aborted.")
            sys.exit(1)

    try:
        token_data = provider.exchange_token(code)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Login failed: {exc}")
        sys.exit(1)

    store.save_token(provider_name, token_data)
    print(f"Successfully authenticated with {provider_name}!")


def _cmd_provider_logout(store: "TokenStore", provider_name: str) -> None:
    if provider_name not in PROVIDERS:
        print(f"Error: Unknown provider '{provider_name}'")
        sys.exit(1)

    if store.delete_token(provider_name):
        print(f"Logged out of {provider_name}.")
    else:
        print(f"{provider_name} was not authenticated.")


def _format_usage_line(name: str, usage: Dict[str, Any]) -> str:
    remaining, limit, used = usage.get("remaining"), usage.get("limit"), usage.get("used")
    if remaining is not None and limit is not None:
        line = f"  [{name}]: {remaining} / {limit} remaining"
    elif used is not None:
        line = f"  [{name}]: {used} used this period (no hard remaining-quota API)"
    else:
        line = f"  [{name}]: usage unknown"
    if usage.get("account"):
        line += f"\n      account: {usage['account']}"
    if usage.get("note"):
        line += f"\n      note: {usage['note']}"
    return line


def main() -> None:
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    store = TokenStore()
    if not store.available:
        print("Error: cannot reach Redis — OAuth provider state cannot be read or saved.")
        sys.exit(1)

    if cmd == "/provider":
        if len(args) == 0:
            print("Available providers:")
            for p in PROVIDERS:
                status = " (Authenticated)" if store.get_token(p) else ""
                if p in RISK_NOTICES:
                    status += " [accepted-risk provider — 'login' prints why]"
                print(f"  - {p}{status}")
        elif len(args) >= 2 and args[0] == "login":
            _cmd_provider_login(store, args[1])
        elif len(args) >= 2 and args[0] == "logout":
            _cmd_provider_logout(store, args[1])
        else:
            print_help()

    elif cmd == "/usage":
        tokens = store.get_all_tokens()
        if not tokens:
            print("No authenticated providers. Use '/provider login [name]' first.")
            sys.exit(0)

        print("Provider Quota/Usage:")
        for name, token_data in tokens.items():
            provider = PROVIDERS.get(name)
            if provider is None:
                continue
            try:
                usage = provider.get_usage(token_data)
                print(_format_usage_line(name, usage))
            except Exception as exc:  # pylint: disable=broad-except
                print(f"  [{name}]: Error fetching usage: {exc}")
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
