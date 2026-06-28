"""
LLM Client Wrapper for PersonalKM

Provides unified interface to LLM providers:
- MiniMax (primary, OpenAI-compatible)
- OpenAI (fallback)
- No-op (when no API key available)

Usage:
    from bot.llm_clients import get_default_client, MiniMaxClient

    client = get_default_client()
    if client:
        response = client.chat_completions.create(
            model=client.default_model,
            messages=[{"role": "user", "content": "Hello"}]
        )
"""

import logging
import os
from typing import Optional, List, Union, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMClientInfo:
    """Info about an LLM client."""
    provider: str  # "minimax", "openai", "none"
    default_model: str
    available_models: List[str]
    base_url: Optional[str] = None


class MiniMaxClient:
    """
    MiniMax Chat Completions API client.
    
    OpenAI-compatible — uses the same interface as OpenAI Python SDK.
    Only difference: base_url points to api.minimax.io/v1 instead of api.openai.com/v1.
    
    API docs: https://platform.minimax.io/docs/api-reference/text-chat-openai
    """
    
    provider = "minimax"
    base_url = "https://api.minimax.io/v1"
    
    # MiniMax models available via this API
    AVAILABLE_MODELS = [
        "MiniMax-M3",
        "MiniMax-M2.7",
        "MiniMax-M2.7-highspeed",
        "MiniMax-M2.5",
        "MiniMax-M2.5-highspeed",
        "MiniMax-M2.1",
        "MiniMax-M2.1-highspeed",
        "MiniMax-M2",
    ]
    
    # Default model for summarization tasks
    DEFAULT_MODEL = "MiniMax-M3"
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.default_model = model or self.DEFAULT_MODEL
        
        # Use OpenAI SDK with MiniMax's base URL
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            self._using_openai_sdk = True
        except ImportError:
            logger.warning("OpenAI SDK not available, using requests instead")
            self._client = None
            self._using_openai_sdk = False
    
    def chat_completions_create(self, model: str, messages: List[Any], **kwargs):
        """
        Create a chat completion.
        
        Args:
            model: Model ID (e.g., "MiniMax-M3")
            messages: List of {"role": "user"|"assistant"|"system", "content": str}
            **kwargs: Additional params (temperature, max_tokens, etc.)
        
        Returns:
            OpenAI-style response object with .choices[0].message.content
        """
        if self._using_openai_sdk and self._client:
            return self._client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
        else:
            # Fallback: use requests directly
            return self._chat_completions_via_requests(model, messages, **kwargs)
    
    def _chat_completions_via_requests(self, model: str, messages: List[Any], **kwargs):
        """Fallback using requests when OpenAI SDK unavailable."""
        import json
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": model,
            "messages": messages,
        }
        data.update(kwargs)
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60,
        )
        
        if response.status_code != 200:
            raise Exception(f"MiniMax API error: {response.status_code} {response.text}")
        
        return response.json()
    
    def list_models(self) -> List[str]:
        """Return list of available models."""
        return self.AVAILABLE_MODELS.copy()
    
    def is_available(self) -> bool:
        """Check if client can make API calls."""
        if not self.api_key:
            return False
        if self._using_openai_sdk and self._client:
            return True
        # Can still work with requests fallback
        return bool(self.api_key)


class OpenAIClient:
    """
    OpenAI Chat Completions API client.
    
    Used as fallback when MiniMax is unavailable. Also serves as the
    client for OpenAI-compatible local servers (e.g. Ollama) when
    OPENAI_BASE_URL is set to a non-default endpoint.
    """
    
    provider = "openai"
    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    
    AVAILABLE_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]
    
    DEFAULT_MODEL = "gpt-4o-mini"
    
    def __init__(self, api_key: str, model: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.default_model = model or os.getenv("OPENAI_MODEL") or self.DEFAULT_MODEL
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or self.DEFAULT_BASE_URL
        
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self._available = True
        except ImportError:
            logger.warning("OpenAI SDK not available")
            self._client = None
            self._available = False
    
    def chat_completions_create(self, model: str, messages: List[Any], **kwargs):
        """Create a chat completion via OpenAI."""
        if self._client:
            return self._client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
        else:
            raise Exception("OpenAI client not available (SDK not installed)")
    
    def list_models(self) -> List[str]:
        """Return list of available models."""
        return self.AVAILABLE_MODELS.copy()
    
    def is_available(self) -> bool:
        """Check if client can make API calls."""
        return self._available and bool(self.api_key)


class NoOpClient:
    """
    No-operation client when no API key is available.
    
    All methods return None or raise informative errors.
    Used for development/testing without API costs.
    """
    
    provider = "none"
    default_model = "none"
    AVAILABLE_MODELS: List[str] = []
    
    def chat_completions_create(self, model: str, messages: List[Any], **kwargs):
        """Always fails — use only for testing."""
        raise Exception(
            "No LLM API key available. "
            "Set MINIMAX_API_KEY or OPENAI_API_KEY environment variable. "
            "See docs/llm-wiki-v2-plan.md Phase 1 for setup."
        )
    
    def list_models(self) -> List[str]:
        return []
    
    def is_available(self) -> bool:
        return False


def get_minimax_client() -> Optional[MiniMaxClient]:
    """Get MiniMax client if API key is available."""
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        logger.debug("MINIMAX_API_KEY not set")
        return None
    
    model = os.getenv("MINIMAX_MODEL")
    try:
        client = MiniMaxClient(api_key=api_key, model=model)
        if client.is_available():
            logger.info(f"MiniMax client initialized (model: {client.default_model})")
            return client
        else:
            logger.warning("MiniMax client initialized but not available")
            return None
    except Exception as e:
        logger.error(f"Failed to initialize MiniMax client: {e}")
        return None


def _is_local_base_url(url: str) -> bool:
    """True if the URL points at a local OpenAI-compatible server (e.g. Ollama)."""
    if not url:
        return False
    lower = url.lower()
    return any(host in lower for host in ("127.0.0.1", "localhost", "0.0.0.0"))


def _probe_ollama(base_url: str, timeout: float = 1.5) -> bool:
    """Quick reachability probe for an OpenAI-compatible local server
    (Ollama at /v1/models, LM Studio, llama.cpp server, etc.)."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{base_url.rstrip('/')}/models", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_openai_client() -> Optional[OpenAIClient]:
    """Get OpenAI client if API key is available.

    Honors OPENAI_BASE_URL: when it points at a localhost endpoint
    (e.g. http://127.0.0.1:11434/v1 for Ollama), the caller is
    responsible for reachability; for genuine OpenAI cloud we just
    check the SDK is importable.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.debug("OPENAI_API_KEY not set")
        return None

    model = os.getenv("OPENAI_MODEL")
    try:
        client = OpenAIClient(api_key=api_key, model=model)
        if client.is_available():
            logger.info(f"OpenAI client initialized (model: {client.default_model}, base: {client.base_url})")
            return client
        else:
            logger.warning("OpenAI client initialized but not available")
            return None
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None


def get_default_client() -> tuple:
    """
    Get the best available LLM client.

    Priority (configurable via env, no code changes needed):
      1. LOCAL Ollama  — when OPENAI_BASE_URL is a localhost URL
                         AND Ollama is reachable. Zero-cost, on-device.
      2. MiniMax        — when MINIMAX_API_KEY is set (cloud, structured JSON expertise).
      3. OpenAI cloud   — when OPENAI_API_KEY is set without a localhost OPENAI_BASE_URL.
      4. NoOp           — graceful degradation (skip_llm=True downstream).

    Returns:
        Tuple of (client, client_info). client is never None.
    """
    # 1) Local Ollama (OpenAI-compatible) — preferred default on Mac Mini.
    base_url = os.getenv("OPENAI_BASE_URL", "")
    api_key = os.getenv("OPENAI_API_KEY")
    if _is_local_base_url(base_url) and api_key:
        if _probe_ollama(base_url):
            client = OpenAIClient(api_key=api_key, model=os.getenv("OPENAI_MODEL"))
            if client.is_available():
                logger.info(f"Local LLM OK: {base_url} model={client.default_model}")
                info = LLMClientInfo(
                    provider="ollama-local",
                    default_model=client.default_model,
                    available_models=client.list_models(),
                    base_url=client.base_url,
                )
                return client, info
            logger.warning(f"Local LLM at {base_url} reachable, but OpenAI SDK init failed")
        else:
            logger.warning(
                f"OPENAI_BASE_URL={base_url} but server not reachable — falling through to MiniMax"
            )

    # 2) MiniMax cloud
    minimax = get_minimax_client()
    if minimax:
        info = LLMClientInfo(
            provider="minimax",
            default_model=minimax.default_model,
            available_models=minimax.list_models(),
            base_url=minimax.base_url,
        )
        return minimax, info

    # 3) OpenAI cloud
    openai = get_openai_client()
    if openai:
        info = LLMClientInfo(
            provider="openai",
            default_model=openai.default_model,
            available_models=openai.list_models(),
            base_url=openai.base_url,
        )
        return openai, info

    # 4) No API key available — return no-op client
    logger.warning(
        "No LLM API key found. Set MINIMAX_API_KEY or OPENAI_API_KEY. "
        "LLM features will be disabled."
    )
    return NoOpClient(), LLMClientInfo(
        provider="none",
        default_model="none",
        available_models=[],
    )


# Convenience function for single-client access
_default_client = None
_default_info = None

def get_llm_client():
    """
    Get the default LLM client (singleton pattern).
    
    Caches the client after first call — environment variables
    are read at startup, not dynamically.
    """
    global _default_client, _default_info
    if _default_client is None:
        _default_client, _default_info = get_default_client()
    return _default_client


def get_llm_info() -> LLMClientInfo:
    """Get info about the default LLM client."""
    global _default_info
    if _default_info is None:
        get_llm_client()  # Initializes both
    # _default_info is always set by get_default_client() returning a NoOpClient if needed
    assert _default_info is not None
    return _default_info


# Test when run directly
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("LLM Client Test")
    print("=" * 60)
    
    client, info = get_default_client()
    
    print(f"Provider:    {info.provider}")
    print(f"Default:     {info.default_model}")
    print(f"Base URL:    {info.base_url or 'N/A'}")
    print(f"Models:      {', '.join(info.available_models[:5])}")
    print(f"Available:   {client.is_available()}")
    print()
    
    if client.is_available():
        print("Testing API call...")
        try:
            response = client.chat_completions_create(
                model=info.default_model,
                messages=[{"role": "user", "content": "Say 'Hello from {info.provider}' in exactly those words."}],
                max_tokens=50,
                temperature=0.1,
            )
            content = response.choices[0].message.content if hasattr(response, 'choices') else response.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"Response:    {content}")
            print("✅ API call successful!")
        except Exception as e:
            print(f"❌ API call failed: {e}")
            sys.exit(1)
    else:
        print("⚠️  No API key available — set MINIMAX_API_KEY or OPENAI_API_KEY")
        print("   LLM features will be disabled until API key is configured.")
        sys.exit(0)
    
    print("=" * 60)
