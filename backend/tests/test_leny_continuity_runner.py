"""Normal session refresh and packet privacy with HTTP doubles only."""
import importlib.util
import json
from pathlib import Path
import sys
import httpx
from scripts import run_leny_spec03_review as runner


def test_long_job_refreshes_access_between_cases_without_persisting_tokens(monkeypatch):
    calls=[]
    def transport(request):
        calls.append(request.url.path)
        if request.url.path.endswith('/refresh'):return httpx.Response(200,json={'access_token':'synthetic-memory-only'})
        return httpx.Response(200,json={'id':7})
    with httpx.Client(base_url='http://127.0.0.1:8000/api/v1',transport=httpx.MockTransport(transport)) as client:
        client._leny_last_refresh=100
        monkeypatch.setattr(runner.time,'monotonic',lambda:300)
        runner.refresh_auth(client)
        assert calls==['/api/v1/auth/me','/api/v1/auth/refresh','/api/v1/auth/me']
        assert client.headers['Authorization']=='Bearer synthetic-memory-only'
        assert client._leny_last_refresh==300


def test_current_session_does_not_rotate_for_every_question(monkeypatch):
    calls=[]
    def transport(request):calls.append(request.url.path);return httpx.Response(200,json={'id':7})
    with httpx.Client(base_url='http://127.0.0.1:8000/api/v1',transport=httpx.MockTransport(transport)) as client:
        client._leny_last_refresh=100
        monkeypatch.setattr(runner.time,'monotonic',lambda:200)
        runner.refresh_auth(client)
    assert calls==['/api/v1/auth/me']
