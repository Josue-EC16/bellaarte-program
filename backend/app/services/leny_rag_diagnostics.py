"""Allowlisted, content-free pipeline diagnostics. Never accepts arbitrary text."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
import re
from time import monotonic

_CODE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
COUNTS = {'inference_calls_total', 'prompt_tokens_total', 'output_tokens_total', 'calls_without_token_counts', 'candidates', 'selected', 'evidence_bytes', 'prompt_bytes', 'prompt_eval_count',
          'eval_count', 'prompt_eval_cached_count', 'citations', 'topic_questions',
          'probe_count', 'probe_prompt_tokens', 'documented_excerpt', 'grounded_excerpt', 'unsupported_request', 'review_documents',
          'coverage_checked', 'coverage_accepted', 'synthesis_validated', 'synthesis_fallback',
          'synthesis_context_fallback', 'synthesis_invalid_fallback'}
COUNTS.update('synthesis_failure_'+kind for kind in ('budget','json','truncated','reference','support_unverified','scope','structure'))
COUNTS.add('thinking_tokens_total')
COUNTS.update({'context_pairs','context_references','context_partial'})
COUNTS.update('synthesis_'+part+'_token_upper_estimate' for part in ('instructions','history','question','evidence','schema'))
DURATIONS = {'routing', 'embedding_and_release', 'search', 'context', 'review', 'selection', 'generation',
             'first_content', 'total', 'load', 'prompt_eval', 'eval', 'provider_total', 'context_probe', 'render', 'coverage', 'synthesis','validation'}


@dataclass
class RagDiagnostics:
    profile: str
    started: float = field(default_factory=monotonic)
    counts: dict = field(default_factory=dict)
    durations: dict = field(default_factory=dict)
    route: str = 'pending'
    reason: str = 'pending'
    verdict: str = 'pending'
    outcome: str = 'pending'

    def count(self, name, value):
        if name not in COUNTS or isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError('Invalid diagnostic count')
        self.counts[name] = value

    def duration(self, name, value):
        if name not in DURATIONS or isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
            raise ValueError('Invalid diagnostic duration')
        self.durations[name] = float(value)

    def snapshot(self):
        codes = (self.profile, self.route, self.reason, self.verdict, self.outcome)
        if any(not isinstance(value, str) or not _CODE.fullmatch(value) for value in codes):
            raise ValueError('Invalid diagnostic code')
        return dict(profile=self.profile, route=self.route, reason=self.reason, verdict=self.verdict,
                    outcome=self.outcome, counts=dict(self.counts), durations_seconds=dict(self.durations))
