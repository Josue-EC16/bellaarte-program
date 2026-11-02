"""Opt-in, local coverage prototype. No DB, model, HTTP or gold access.

The selector's self-reported relevance is deliberately not an input. A reviewed
manifest is trusted annotation, not a machine proof of semantic correctness.
Research mode can inspect DRAFT annotations, but can NEVER authorize release.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import re
import unicodedata
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

COVERAGE_VERSION = 'coverage-prototype-v1'
COVERAGE_POLICY_VERSION = 'rag4-cov-p1'


def digest(value: str) -> str:
    return sha256(value.encode('utf-8')).hexdigest()


def fingerprint(value: dict) -> str:
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')))


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Approval(Contract):
    state: Literal['draft', 'approved', 'withdrawn'] = 'draft'
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    human_reviewed: bool = False

    @model_validator(mode='after')
    def approved_identity(self):
        if self.state == 'approved' and (not self.human_reviewed or not self.reviewed_by
                                        or not self.reviewed_by.strip() or not self.reviewed_at):
            raise ValueError('An approval requires a recorded human review')
        if self.reviewed_at:
            from datetime import datetime
            stamp = datetime.fromisoformat(self.reviewed_at)
            if stamp.tzinfo is None:
                raise ValueError('Review timestamp must include timezone')
        return self


class Concept(Contract):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal['topic', 'aspect', 'qualifier']
    aliases: list[str] = Field(min_length=1, max_length=100)
    parents: list[str] = Field(default_factory=list, max_length=10)


class Vocabulary(Contract):
    version: str = Field(min_length=1, max_length=64)
    approval: Approval = Field(default_factory=Approval)
    concepts: list[Concept] = Field(min_length=1, max_length=300)
    grammar_words: list[str] = Field(default_factory=list, max_length=500)
    presentation_phrases: list[str] = Field(default_factory=list, max_length=80)
    complete_phrases: list[str] = Field(default_factory=list, max_length=40)
    comparison_phrases: list[str] = Field(default_factory=list, max_length=30)
    followup_phrases: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode='after')
    def valid_concepts(self):
        known = {c.id: c for c in self.concepts}
        if len(known) != len(self.concepts):
            raise ValueError('Duplicate conceptual identity')
        for c in self.concepts:
            if any(p not in known or p == c.id or known[p].kind != c.kind for p in c.parents):
                raise ValueError('Invalid conceptual parent')
            if any(not _tokens(a) or len(a) > 160 for a in c.aliases):
                raise ValueError('Invalid conceptual alias')
        for start in known:
            pending, visited = list(known[start].parents), {start}
            while pending:
                item = pending.pop()
                if item == start:
                    raise ValueError('Cyclic conceptual ancestry')
                if item not in visited:
                    visited.add(item)
                    pending.extend(known[item].parents)
        return self


class Span(Contract):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class Assertion(Contract):
    predicate: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=100)
    unit: str = Field(default='', max_length=40)
    condition: str = Field(default='', max_length=160)


class Unit(Contract):
    fragment_id: str = Field(min_length=1)
    text_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    spans: list[Span] = Field(min_length=1, max_length=100)
    topics: list[str] = Field(min_length=1, max_length=30)
    aspects: list[str] = Field(min_length=1, max_length=20)
    qualifiers: list[str] = Field(default_factory=list, max_length=20)
    required_fragment_ids: list[str] = Field(default_factory=list, max_length=20)
    assertions: list[Assertion] = Field(default_factory=list, max_length=30)


class Procedure(Contract):
    topic: str
    fragments: list[str] = Field(min_length=1, max_length=100)


class Manifest(Contract):
    schema_version: Literal['coverage-manifest-v1'] = 'coverage-manifest-v1'
    revision: int = Field(ge=1)
    document_id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)
    indexation_id: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_hash_basis: Literal['original_file', 'synthetic_virtual_document']
    vocabulary_version: str
    approval: Approval = Field(default_factory=Approval)
    units: list[Unit] = Field(min_length=1, max_length=10000)
    procedures: list[Procedure] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def valid_units(self):
        ids = [u.fragment_id for u in self.units]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate support unit')
        if any(f not in ids for u in self.units for f in u.required_fragment_ids):
            raise ValueError('Foreign support dependency')
        if any(f not in ids for p in self.procedures for f in p.fragments):
            raise ValueError('Foreign procedure part')
        return self


class CoverageProvider(Protocol):
    def vocabulary(self) -> Vocabulary: ...
    def manifests(self, rows: list[dict]) -> list[Manifest]: ...


class MemoryCoverageProvider:
    """Experimental adapter. No production wiring or automatic approval API."""
    def __init__(self, vocabulary: dict, manifests: list[dict]):
        self._vocabulary = deepcopy(vocabulary)
        self._manifests = deepcopy(manifests)

    def vocabulary(self):
        return Vocabulary.model_validate(deepcopy(self._vocabulary))

    def manifests(self, rows):
        # Only metadata belonging to the caller's already-authorized rows.
        documents = {str(r['document_id']) for r in rows}
        return [Manifest.model_validate(deepcopy(m)) for m in self._manifests
                if m['document_id'] in documents]


def _normal(value):
    output, positions = [], []
    for i, character in enumerate(value):
        for char in unicodedata.normalize('NFKD', character.casefold()):
            if not unicodedata.combining(char):
                output.append(char)
                positions.append(i)
    return ''.join(output), positions


def _tokens(value):
    return re.findall(r'[a-z0-9]+(?:[.,][0-9]+)?%?', _normal(value)[0])


def resolve_request(question: str, vocabulary: Vocabulary, history=()) -> dict:
    """Bounded compositional matching; unresolved meaning stays uncertain.

    Aliases are human proposals in a versioned catalogue, never gold. All
    substantive residual tokens and nontrivial logical operators are visible.
    The prototype deliberately does not pretend to parse unrestricted Spanish.
    """
    if not isinstance(question, str) or not question.strip() or len(question) > 8000:
        raise ValueError('Invalid bounded coverage question')
    query = question
    from_anchor = False
    if _tokens(query) in [_tokens(p) for p in vocabulary.followup_phrases]:
        anchors = [h for h in history if h.get('role') == 'user' and h.get('documentary') is True]
        if not anchors or len(anchors[-1]['content']) >= 400:
            return {'topics': [], 'aspects': [], 'qualifiers': [], 'spans': [],
                    'unknown': [], 'complete': False, 'compare': False, 'reason': 'coverage_anchor_uncertain'}
        query = anchors[-1]['content']
        from_anchor = True
    # A claimed role can be search noise, never an authority or account identity.
    query = re.sub(r'\s+como\s+(?:ADMIN|CAJA|INV_BOUTIQUE|INV_TALLER|MODISTA)\s*[.!?]*$', '', query, flags=re.I)
    plain, positions = _normal(query)
    found = list(re.finditer(r'[a-z0-9]+(?:[.,][0-9]+)?%?', plain))
    words = [m.group() for m in found]
    covered, labels, spans = set(), {'topic': set(), 'aspect': set(), 'qualifier': set()}, []
    options = []
    for c in vocabulary.concepts:
        for alias in c.aliases:
            parts = _tokens(alias)
            for i in range(len(words)-len(parts)+1):
                if words[i:i+len(parts)] == parts:
                    options.append((len(parts), i, c))
    ambiguous_alias = False
    # Longest phrase wins; no broad single-word match can erase a qualifier.
    for length, i, c in sorted(options, key=lambda x: (-x[0], x[1], x[2].id)):
        if any(j in covered for j in range(i, i+length)):
            continue
        alternatives = {other.id for size, start, other in options if size == length and start == i}
        if len(alternatives) > 1:
            ambiguous_alias = True
            covered.update(range(i, i+length))
            continue
        covered.update(range(i, i+length))
        labels[c.kind].add(c.id)
        spans.append({'concept': c.id, 'kind': c.kind, 'start': positions[found[i].start()],
                      'end': positions[found[i+length-1].end()-1]+1, 'origin': 'user_topic' if from_anchor else 'current_user'})
    # Presentation affects neither scope nor coverage. Never discard other clauses.
    for phrase in vocabulary.presentation_phrases:
        parts = _tokens(phrase)
        for i in range(len(words)-len(parts)+1):
            if words[i:i+len(parts)] == parts:
                covered.update(range(i, i+len(parts)))
    grammar = set(vocabulary.grammar_words)
    unknown = [dict(token=w, start=positions[found[i].start()], end=positions[found[i].end()-1]+1)
               for i, w in enumerate(words) if i not in covered and w not in grammar]
    # Negation/alternatives/conditional clauses require a semantic parser that
    # this bounded prototype does not have. They cannot be ignored as stopwords.
    logic = any(w in {'no', 'sin', 'nunca', 'excepto', 'ni', 'o', 'si'} for w in words)
    contains = lambda phrases: any(re.search(r'\b'+re.escape(_normal(p)[0])+r'\b', plain) for p in phrases)
    return dict(topics=sorted(labels['topic']), aspects=sorted(labels['aspect']),
                qualifiers=sorted(labels['qualifier']), spans=spans, unknown=unknown,
                complete=contains(vocabulary.complete_phrases), compare=contains(vocabulary.comparison_phrases),
                reason='coverage_alias_ambiguous' if ambiguous_alias else 'coverage_logic_uncertain' if logic else 'coverage_terms_uncertain' if unknown
                       else 'coverage_subject_uncertain' if not labels['topic'] else 'coverage_intent_resolved')


@dataclass(frozen=True)
class CoverageDecision:
    verdict: str
    reason: str
    fragment_ids: tuple[str, ...] = ()
    manifest_fingerprints: tuple[str, ...] = ()
    authoritative: bool = False
    signature: dict | None = None

    @property
    def release_allowed(self):
        return self.authoritative and self.verdict in {'approved', 'partial', 'conflicting'}


class CoverageVerifier:
    def __init__(self, provider: CoverageProvider):
        self.provider = provider

    def evaluate(self, question, rows, *, history=(), research=False):
        vocabulary = self.provider.vocabulary()
        signature = resolve_request(question, vocabulary, history)
        result = lambda v, r, **kw: CoverageDecision(v, r, signature=signature, **kw)
        if len(rows) > 5 or len({str(r['fragment_id']) for r in rows}) != len(rows):
            raise ValueError('Invalid final evidence size or duplicate identity')
        if not rows:
            return result('not_covered', 'coverage_evidence_empty')
        manifests = self.provider.manifests(rows)
        if len({(m.document_id, m.version_id, m.indexation_id) for m in manifests}) != len(manifests):
            raise ValueError('Ambiguous coverage revision')
        authoritative = vocabulary.approval.state == 'approved'
        if vocabulary.approval.state == 'withdrawn':
            return result('uncertain', 'coverage_vocabulary_withdrawn')
        bound, fingerprints = [], [fingerprint(vocabulary.model_dump())]
        known = {c.id: c.kind for c in vocabulary.concepts}
        for row in rows:
            matches = [m for m in manifests if (m.document_id, m.version_id, m.indexation_id) ==
                       tuple(str(row[k]) for k in ('document_id', 'version_id', 'indexation_id'))]
            if not matches:
                return result('uncertain', 'coverage_manifest_missing')
            m = matches[0]
            if m.approval.state == 'withdrawn':
                return result('uncertain', 'coverage_manifest_withdrawn')
            if m.vocabulary_version != vocabulary.version:
                return result('uncertain', 'coverage_vocabulary_stale')
            if row.get('source_sha256') != m.source_sha256:
                return result('uncertain', 'coverage_original_hash_unverified')
            unit = next((u for u in m.units if u.fragment_id == str(row['fragment_id'])), None)
            if unit is None or digest(row['text']) != unit.text_sha256:
                return result('uncertain', 'coverage_fragment_hash_changed')
            # Full emitted fragment must be annotated. Isolated relevant spans
            # cannot bless unexamined adjacent assertions in the same fragment.
            cursor = 0
            for span in sorted(unit.spans, key=lambda s: s.start):
                if span.start != cursor or span.end <= span.start or span.end > len(row['text']):
                    return result('uncertain', 'coverage_span_incomplete')
                if digest(row['text'][span.start:span.end]) != span.sha256:
                    return result('uncertain', 'coverage_span_hash_changed')
                cursor = span.end
            if cursor != len(row['text']):
                return result('uncertain', 'coverage_span_incomplete')
            if any(not re.search(r'(?<!\w)'+re.escape(a.value)+r'(?!\w)', row['text']) for a in unit.assertions):
                return result('uncertain', 'coverage_assertion_unbacked')
            for field, kind in [('topics', 'topic'), ('aspects', 'aspect'), ('qualifiers', 'qualifier')]:
                if any(known.get(x) != kind for x in getattr(unit, field)):
                    raise ValueError('Unknown or mistyped manifest concept')
            authoritative = authoritative and m.approval.state == 'approved'
            bound.append((row, m, unit))
            fingerprints.append(fingerprint(m.model_dump()))
        if not authoritative and not research:
            return result('uncertain', 'coverage_human_review_pending')
        if signature['reason'] != 'coverage_intent_resolved':
            return result('uncertain', signature['reason'])
        topics, aspects, qualifiers = map(set, (signature['topics'], signature['aspects'], signature['qualifiers']))
        supported_topics = set().union(*(set(u.topics) for _, _, u in bound))
        if not topics <= supported_topics:
            return result('not_covered', 'coverage_subject_mismatch')
        if not qualifiers <= set().union(*(set(u.qualifiers) for _, _, u in bound)):
            return result('not_covered', 'coverage_specialization_not_supported')
        if any(not qualifiers <= set(u.qualifiers) for _, _, u in bound):
            return result('not_covered', 'coverage_specialization_not_supported')
        if any(not set(u.qualifiers) <= qualifiers for _, _, u in bound):
            return result('not_covered', 'coverage_narrower_scope')
        # Every output unit must support the requested subject, including parts
        # added by expansion. Parent topic membership never grants child scope.
        if any(not topics.intersection(u.topics) for _, _, u in bound):
            return result('not_covered', 'coverage_tangential_unit')
        available_aspects = set().union(*(set(u.aspects) for _, _, u in bound))
        if aspects and not aspects.intersection(available_aspects):
            return result('not_covered', 'coverage_aspect_not_supported')
        partial = bool(aspects-available_aspects)
        if len(topics) > 1 and len(aspects) > 1 and any(not aspects <= set(u.aspects) for _, _, u in bound):
            # This bounded parser cannot assign different requested aspects to
            # different subjects. Union coverage is not proof of that relation.
            return result('uncertain', 'coverage_relations_uncertain')
        if partial:
            signature['uncovered_aspects'] = sorted(aspects-available_aspects)
        ids = {str(r['fragment_id']) for r in rows}
        if any(not set(u.required_fragment_ids) <= ids for _, _, u in bound):
            return result('uncertain', 'coverage_condition_dependency_missing')
        if aspects:
            relevant = {u.fragment_id for _, _, u in bound if aspects.intersection(u.aspects)}
            for _ in range(len(bound)):
                relevant.update(f for _, _, u in bound if u.fragment_id in relevant for f in u.required_fragment_ids)
            if not ids <= relevant:
                return result('not_covered', 'coverage_tangential_aspect')
        if signature['complete']:
            concepts = {c.id: c for c in vocabulary.concepts}
            for topic in topics:
                family, pending = {topic}, list(concepts[topic].parents)
                while pending:
                    parent = pending.pop()
                    if parent not in family:
                        family.add(parent)
                        pending.extend(concepts[parent].parents)
                procedures = [p for _, m, _ in bound for p in m.procedures if p.topic in family]
                if not procedures:
                    return result('uncertain', 'coverage_completeness_undeclared')
                for procedure in procedures:
                    if not set(procedure.fragments) <= ids:
                        return result('uncertain', 'coverage_procedure_incomplete')
        claims = {}
        for _, _, u in bound:
            for assertion in u.assertions:
                key = (tuple(sorted(set(u.topics) & topics)), assertion.predicate, assertion.unit, assertion.condition)
                claims.setdefault(key, set()).add(assertion.value)
        conflict = any(len(values) > 1 for values in claims.values())
        return result('conflicting' if conflict else 'partial' if partial else 'approved',
                      'coverage_conflicting_support' if conflict else 'coverage_partial_support' if partial else 'coverage_verified',
                      fragment_ids=tuple(str(r['fragment_id']) for r in rows),
                      manifest_fingerprints=tuple(sorted(set(fingerprints))), authoritative=bool(authoritative and not research))
