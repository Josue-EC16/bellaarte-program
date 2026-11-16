"""No Google/app/production DB calls: diagnostic gates and account quota."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from app.core.config import Settings


def diagnostic():
    path=Path(__file__).parents[1]/'scripts/diagnose_leny_gemini_spec021.py'
    spec=importlib.util.spec_from_file_location('leny_gemini_diagnostic_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_owner_supplied_flash31_quotas_cannot_be_overridden_upward(monkeypatch):
    monkeypatch.delenv('LENY_GEMINI_RPD',raising=False)
    c=Settings(_env_file=None,environment='test')
    assert c.leny_gemini_rpd==500 and c.leny_gemini_rpm==15 and not c.leny_gemini_enabled
    assert c.leny_gemini_thinking_level=='medium' and c.leny_gemini_input_token_budget==32678
    for value in (501,1000):
        with pytest.raises(ValidationError):Settings(_env_file=None,leny_gemini_rpd=value)
    with pytest.raises(ValidationError):Settings(_env_file=None,leny_gemini_rpm=16)


@pytest.mark.parametrize('step,results',[
    ('B',{}),('B',{'A':False}),('C',{'A':False,'B':True}),('C',{'A':True,'B':False}),('C',{'A':True}),
])
def test_failed_or_missing_predecessor_cannot_unlock_google_calls(tmp_path,step,results):
    module=diagnostic()
    for name,passed in results.items():
        (tmp_path/(name+'.json')).write_text(json.dumps({'passed':passed}),encoding='utf-8')
    with pytest.raises(RuntimeError,match='Previous diagnostic step'):module.prerequisite(tmp_path,step)


def test_both_successful_predecessors_unlock_only_the_next_step(tmp_path):
    module=diagnostic()
    for name in ('A','B'):(tmp_path/(name+'.json')).write_text('{"passed":true}',encoding='utf-8')
    module.prerequisite(tmp_path,'C')


def test_completed_text_excludes_thoughts_and_does_not_certify_truncation():
    module=diagnostic()
    result=SimpleNamespace(candidates=[SimpleNamespace(finish_reason='MAX_TOKENS',
        content=SimpleNamespace(parts=[SimpleNamespace(text='PRIVATE_THOUGHT',thought=True),
                                       SimpleNamespace(text='partial',thought=False)]))])
    assert module.completed_text(result)==('partial','MAX_TOKENS')
    assert module.completed_text(SimpleNamespace(candidates=[]))==('',None)
