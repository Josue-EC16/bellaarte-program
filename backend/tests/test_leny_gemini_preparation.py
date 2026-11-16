"""Phase 1 contracts: fake keys, no SDK client and no external traffic."""
import asyncio
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.leny_llm_contracts import Capability, ChatProvider, LenyError
from app.services.leny_llm_providers import create_provider
from app.services.leny_ollama import OllamaProvider


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('No network allowed in Gemini phase 1 tests')
    monkeypatch.setattr(socket, 'getaddrinfo', blocked)
    # Windows asyncio creates a local socketpair for its event-loop wakeup.
    # Permit that numeric loopback only; external DNS/connect remain forbidden.
    for name in ('connect', 'connect_ex'):
        original = getattr(socket.socket, name)
        def guarded(sock, address, _original=original):
            if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1'):
                return _original(sock, address)
            return blocked()
        monkeypatch.setattr(socket.socket, name, guarded)


def config(**changes):
    return Settings(_env_file=None, environment='test', **changes)


def test_defaults_and_existing_import_identity():
    from app.services.leny_ollama import ChatProvider as OldProtocol, LenyError as OldError
    c = config()
    assert c.leny_llm_provider == 'ollama' and not c.leny_gemini_enabled
    assert c.gemini_api_key is None
    assert OldProtocol is ChatProvider and OldError is LenyError
    p = create_provider(c)
    assert isinstance(p, OllamaProvider) and isinstance(p, ChatProvider)
    assert p.config is c and p.capabilities.streaming == Capability.SUPPORTED


@pytest.mark.parametrize('changes', [dict(leny_llm_provider='unknown'), dict(leny_gemini_model=''),
    dict(leny_gemini_model=' '), dict(leny_gemini_timeout_seconds=0),
    dict(leny_gemini_timeout_seconds=-1), dict(leny_gemini_timeout_seconds=float('inf')),
    dict(leny_gemini_timeout_seconds=float('nan'))])
def test_invalid_configuration_hides_input(changes):
    with pytest.raises(ValidationError) as caught:
        config(gemini_api_key='SYNTHETIC_PRIVATE_KEY', **changes)
    assert 'SYNTHETIC_PRIVATE_KEY' not in str(caught.value)


def test_key_excluded_from_configuration_and_public_diagnostics(monkeypatch):
    from app.services.leny_service import LenyService
    monkeypatch.setenv('GEMINI_API_KEY', 'SYNTHETIC_PRIVATE_KEY')
    c = config()
    assert c.gemini_api_key.get_secret_value() == 'SYNTHETIC_PRIVATE_KEY'
    assert 'gemini_api_key' not in c.model_dump()
    assert 'SYNTHETIC_PRIVATE_KEY' not in repr(c)+c.model_dump_json()
    service = LenyService(c, Mock(), Mock())
    assert 'SYNTHETIC_PRIVATE_KEY' not in json.dumps(service.admin_config())
    injected = Mock()
    assert LenyService(c, Mock(), Mock(), provider_factory=injected).provider_factory is injected
    assert isinstance(service.provider_factory(), OllamaProvider)


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('key', [None, 'SYNTHETIC_PRIVATE_KEY'])
def test_every_gemini_operation_rejects_without_constructing_client(enabled, key, monkeypatch):
    from google import genai
    client = Mock(side_effect=AssertionError('SDK client forbidden'))
    monkeypatch.setattr(genai, 'Client', client)
    p = create_provider(config(leny_llm_provider='gemini', leny_gemini_enabled=enabled, gemini_api_key=key))
    assert isinstance(p, ChatProvider)
    assert all(value == Capability.SUPPORTED for value in vars(p.capabilities).values())
    async def scenario():
        async def streaming():
            return [part async for part in p.stream([])]
        for call in (p.available, lambda: p.classify([], {}), lambda: p.structured([], {}),
                     lambda: p.measure_prompt([], schema={}), streaming):
            with pytest.raises(LenyError) as caught:
                await call()
            assert caught.value.code == ('LENY_GEMINI_TIER' if enabled else 'LENY_GEMINI_DISABLED')
            assert 'SYNTHETIC_PRIVATE_KEY' not in str(caught.value)
        assert not p.inference_started and not p.response_complete and not p.metrics
    asyncio.run(scenario())
    client.assert_not_called()


def test_unknown_provider_does_not_fall_back():
    with pytest.raises(LenyError, match='permitido'):
        create_provider(SimpleNamespace(leny_llm_provider='untrusted.module'))


def test_default_service_import_does_not_import_google_or_open_network():
    backend = Path(__file__).resolve().parents[1]
    code = '''
import builtins,socket
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name=='google' or name.startswith('google.'):
        raise AssertionError('Default LENY must not import Google SDK')
    return original(name,*args,**kwargs)
builtins.__import__=guarded
def blocked(*args,**kwargs):raise AssertionError('Network forbidden')
socket.getaddrinfo=blocked
socket.socket.connect=blocked
from app.core.config import Settings
from app.services.leny_service import LenyService
from app.services.leny_ollama import OllamaProvider
config=Settings(_env_file=None,environment='test')
assert isinstance(LenyService(config,None,None).provider_factory(),OllamaProvider)
'''
    env = dict(os.environ, PYTHONPATH=str(backend), ENVIRONMENT='test', LENY_RUNTIME_AUTOSTART='false',
        DATABASE_URL='postgresql+psycopg2://unit_only@127.0.0.1:1/unit_only',
        LENY_LLM_PROVIDER='ollama', LENY_GEMINI_ENABLED='false')
    result = subprocess.run([sys.executable,'-B','-c',code], cwd=backend, env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
