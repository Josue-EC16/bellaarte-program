"""Bounded exact next-point excerpts from freshly authorized numbered sources.

This is not a general Spanish parser or proof of workflow chronology. It only
identifies an explicitly mentioned initial infinitive and the next numbered
point of the same current index. Ambiguity requests clarification, never an
invented business step. No old assistant/document text is accepted.
"""
from __future__ import annotations

import re

from app.services.leny_guard import normalized, has_secret, ROLE_MARKER, FALSE_ACTION
from app.services.leny_policy import deterministic_decision

POINT = re.compile(r'(?<![\w.])([1-9]\d{0,2})\.\s+(?=[^\W\d_])')
WORD = re.compile(r'[^\W\d_]+', re.UNICODE)
CLAUSE_BOUNDARY = re.compile(r'[;,.!?]|\b(?:y|e|luego|después|entonces)\b')
SUFFIX = re.compile(r'(?:ar|er|ir|a|e|o|an|en|as|es|amos|emos|imos|ado|ada|ados|adas|'
                    r'ido|ida|idos|idas|ando|iendo|é|ó|aron|ieron|aba|aban)')
NON_OBJECTS = {'antes', 'después', 'únicamente', 'primero', 'luego', 'cuando', 'siempre',
               'solamente', 'documento', 'documentado', 'evaluación', 'ficticio'}


def quote_document_text(value):
    """Source markup is data: HTML/comments/links must remain visible text."""
    return re.sub(r'([\\`*_{}\[\]<>#!|])', r'\\\1', value)


def next_documented_point(prior_user_question, rows, *, continuation=False):
    """Return (text, clarification); every quote/citation uses the input rows."""
    groups, duplicated = {}, set()
    for index, row in enumerate(rows):
        group = row.get('indexation_id') or row.get('document_id') or row['fragment_id']
        points = groups.setdefault(group, {})
        matches = list(POINT.finditer(row['text']))
        for position, match in enumerate(matches):
            number = int(match.group(1))
            end = matches[position+1].start() if position+1 < len(matches) else len(row['text'])
            value = row['text'][match.end():end].strip()
            if number in points:
                duplicated.add(group)
            points[number] = (value, 'S'+str(index+1))
    prior = normalized(prior_user_question)
    words = list(WORD.finditer(prior))
    boundaries = list(CLAUSE_BOUNDARY.finditer(prior))
    # A small literal matcher cannot reliably resolve the scope of negations,
    # conditional future plans, or duplicate numbering across sections. Never
    # erase that uncertainty by choosing a different apparently valid source.
    ambiguous_scope = bool(duplicated or re.search(r'\b(?:no|sin|nunca|ni|antes de)\b', prior))
    anchors, uncertain = [], []
    for group, points in groups.items():
        if group in duplicated:
            continue
        for number, (value, _source) in points.items():
            first = WORD.match(normalized(value))
            verb = first.group() if first else ''
            if not verb.endswith(('ar', 'er', 'ir')) or len(verb) < 5:
                continue
            stem = verb[:-2]
            objects = {word.group()[:5] for word in WORD.finditer(normalized(value)[len(verb):])
                       if len(word.group()) >= 5 and word.group() not in NON_OBJECTS}
            positions = []
            for word in words:
                if not word.group().startswith(stem) or not SUFFIX.fullmatch(word.group()[len(stem):]):
                    continue
                # An object mentioned with a different coordinated action must
                # not lend that action's verb an apparent workflow anchor.
                # Keep preceding objects for phrases such as "diseño confirmado".
                start = max((item.end() for item in boundaries if item.end() <= word.start()), default=0)
                end = min((item.start() for item in boundaries if item.start() >= word.end()), default=len(prior))
                local_objects = {item.group()[:5] for item in WORD.finditer(prior[start:end])
                                 if len(item.group()) >= 5}
                object_match = bool(objects & local_objects)
                if ambiguous_scope or not object_match:
                    uncertain.append(word.start())
                else:
                    positions.append(word.start())
            if positions:
                anchors.append((max(positions), group, number))
    if anchors:
        last_position = max(item[0] for item in anchors)
        winners = [item for item in anchors if item[0] == last_position]
        if not ambiguous_scope and len(winners) == 1 and not any(position >= last_position for position in uncertain):
            _, group, number = winners[0]
            following = groups[group].get(number+1)
            if following:
                numbers = list(range(number+1, max(groups[group])+1)) if continuation else [number+1]
                if any(item not in groups[group] for item in numbers):
                    return ('La secuencia disponible tiene saltos. Indica la sección que quieres continuar. [S1]', True)
                excerpts = []
                for item in numbers:
                    value, source = groups[group][item]
                    decision = deterministic_decision(value, [])
                    if (has_secret(normalized(value)) or ROLE_MARKER.search(value) or FALSE_ACTION.search(value)
                            or decision and decision.category in {'dangerous', 'manipulation'}):
                        break
                    excerpts.append(str(item)+'. '+quote_document_text(value)+' ['+source+']')
                else:
                    introduction = ('Continuación literal de los puntos numerados de la guía:' if continuation
                                    else 'El siguiente punto numerado de la guía es:')
                    return introduction+'\n\n'+'\n\n'.join(excerpts), False
    reference = ' [S1]' if rows else ''
    return ('Indica la última acción concreta o la sección que quieres continuar. '
            'No puedo determinar con seguridad el siguiente punto a partir de la evidencia disponible.'+reference, True)
