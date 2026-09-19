import sys
import os
import json
import logging
import redis
import time
from typing import Protocol, Optional, Dict, Any

# Adjust path if needed so we can import project modules if required, but maybe not needed here.
# Configure logging for CLI
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("oauth-cli")

_DEFAULT_REDIS_URL = "redis://nesti-redis:6379/0"
_OAUTH_PREFIX = "ai-dev:oauth:tokens:"

class ConsumerProvider(Protocol):
    name: str

    def get_auth_url(self) -> str:
        ...

    def exchange_token(self, code: str) -> Dict[str, Any]:
        ...

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Returns dict with keys: remaining, limit, reset_time"""
        ...

# ---------------------------------------------------------
# Provider Implementations (Stubs)
# ---------------------------------------------------------

class ClaudeProvider:
    name = "claude"

    def get_auth_url(self) -> str:
        return "https://auth.claude.ai/oauth/authorize?client_id=nesti-cli&response_type=code"

    def exchange_token(self, code: str) -> Dict[str, Any]:
        # Stub implementation
        return {
            "access_token": f"mock_claude_token_{code}",
            "expires_in": 3600,
            "provider": self.name
        }

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        # Stub implementation
        return {
            "remaining": 45,
            "limit": 50,
            "reset_time": int(time.time()) + 3600
        }

class AntigravityProvider:
    name = "antigravity"

    def get_auth_url(self) -> str:
        return "https://auth.antigravity.ai/oauth/authorize?client_id=nesti-cli&response_type=code"

    def exchange_token(self, code: str) -> Dict[str, Any]:
        return {
            "access_token": f"mock_antigravity_token_{code}",
            "expires_in": 3600,
            "provider": self.name
        }

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "remaining": 100,
            "limit": 100,
            "reset_time": int(time.time()) + 3600
        }

class CopilotProvider:
    name = "copilot"

    def get_auth_url(self) -> str:
        return "https://github.com/login/oauth/authorize?client_id=nesti-cli&scope=read:user"

    def exchange_token(self, code: str) -> Dict[str, Any]:
        return {
            "access_token": f"mock_copilot_token_{code}",
            "expires_in": 3600,
            "provider": self.name
        }

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "remaining": 500,
            "limit": 500,
            "reset_time": int(time.time()) + 3600
        }

class ChatGPTPlusProvider:
    name = "chatgpt-plus"

    def get_auth_url(self) -> str:
        return "https://auth.openai.com/oauth/authorize?client_id=nesti-cli&response_type=code"

    def exchange_token(self, code: str) -> Dict[str, Any]:
        return {
            "access_token": f"mock_chatgpt_token_{code}",
            "expires_in": 3600,
            "provider": self.name
        }

    def get_usage(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "remaining": 40,
            "limit": 40,
            "reset_time": int(time.time()) + 10800  # 3 hours
        }

PROVIDERS: Dict[str, ConsumerProvider] = {
    "claude": ClaudeProvider(),
    "antigravity": AntigravityProvider(),
    "copilot": CopilotProvider(),
    "chatgpt-plus": ChatGPTPlusProvider()
}

# ---------------------------------------------------------
# Redis State Manager
# ---------------------------------------------------------

class TokenStore:
    def __init__(self):

        redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
        # TokenStore artık graph/nodes.py ve llm_client.py tarafından
        # kütüphane olarak import ediliyor. sys.exit() SystemExit fırlatır
        # (BaseException'dan türer, Exception'dan DEĞİL), bu yüzden çağıran
        # taraflardaki "except Exception" blokları onu YAKALAYAMAZ: Redis'e
        # kısa süreli bir erişilemezlik bile tüm --loop sürecini öldürür —
        # node_cleanup hiç çalışmaz, issue'nun ::in-progress kilidi kalıcı
        # olarak takılı kalır. Sonlandırma kararı artık yalnızca CLI giriş
        # noktasında verilir (main(), aşağıda).
        try:
            self._redis = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)
            self._redis.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis at {redis_url}: {e}") from e

    def save_token(self, provider_name: str, token_data: Dict[str, Any]):
        key = f"{_OAUTH_PREFIX}{provider_name}"
        self._redis.set(key, json.dumps(token_data))

    def get_token(self, provider_name: str) -> Optional[Dict[str, Any]]:
        key = f"{_OAUTH_PREFIX}{provider_name}"
        data = self._redis.get(key)
        if data:
            return json.loads(data)
        return None

    def delete_token(self, provider_name: str) -> None:
        """
        save_token/get_token'dan sonra lazımdı.
        testlerin seed ettiği token'ı temizlemesi ve yarın bi gün bi '/provider logout' için zaten gerekecek."""
        self._redis.delete(f"{_OAUTH_PREFIX}{provider_name}")

    def get_all_tokens(self) -> Dict[str, Dict[str, Any]]:
        tokens = {}
        for provider in PROVIDERS.keys():
            t = self.get_token(provider)
            if t:
                tokens[provider] = t
        return tokens

# ---------------------------------------------------------
# CLI Dispatcher
# ---------------------------------------------------------

def print_help():
    print("Nesti OAuth CLI")
    print("Commands:")
    print("  /provider               List available consumer providers")
    print("  /provider login [name]  Initiate OAuth for a provider")
    print("  /usage                  Show usage/quota for authenticated providers")

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    try:
        store = TokenStore()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)

    if cmd == "/provider":
        if len(args) == 0:
            print("Available providers:")
            for p in PROVIDERS.keys():
                status = " (Authenticated)" if store.get_token(p) else ""
                print(f"  - {p}{status}")
        elif len(args) >= 2 and args[0] == "login":
            provider_name = args[1]
            if provider_name not in PROVIDERS:
                print(f"Error: Unknown provider '{provider_name}'")
                sys.exit(1)
            
            provider = PROVIDERS[provider_name]
            print(f"\nInitiating login for {provider_name}...")
            print(f"Please open the following URL in your browser:\n")
            print(f"  {provider.get_auth_url()}\n")
            
            # Manual callback loop
            try:
                code = input("Paste the authorization code/token here: ").strip()
            except KeyboardInterrupt:
                print("\nLogin cancelled.")
                sys.exit(0)
                
            if not code:
                print("No code provided. Login aborted.")
                sys.exit(1)
                
            token_data = provider.exchange_token(code)
            store.save_token(provider_name, token_data)
            print(f"Successfully authenticated with {provider_name}!")
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
            if provider:
                try:
                    usage = provider.get_usage(token_data)
                    print(f"  [{name}]: {usage.get('remaining', 0)} / {usage.get('limit', '∞')} remaining")
                except Exception as e:
                    print(f"  [{name}]: Error fetching usage: {e}")
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()