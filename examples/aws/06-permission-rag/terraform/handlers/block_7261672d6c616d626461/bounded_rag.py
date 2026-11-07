"""Bounded retrieval core. Identity must come from the authenticated server adapter.

This module is not a deployment adapter. It makes no AWS calls and never accepts
identity or employee region from the question body.
"""
from dataclasses import dataclass
import re
import time
import math
from decimal import Decimal

MAX_DOCUMENTS = 100
MAX_DOCUMENT_BYTES = 8_000
MAX_QUESTION_BYTES = 2_000
MAX_EVIDENCE_BYTES = 12_000
MAX_RESULTS = 4
STOP_WORDS = frozenset('a an the is are was were be to of for and or in on at what how when where who does do it this that'.split())


@dataclass(frozen=True)
class Principal:
    subject: str
    region: str


class RetrievalDenied(Exception):
    """Public callers receive only a generic access failure, never document metadata."""


def terms(text):
    return frozenset(word for word in re.findall(r'\w+', text.casefold()) if word not in STOP_WORDS)


def retrieve(question, documents, principal):
    if not isinstance(principal, Principal) or not principal.subject or not principal.region:
        raise RetrievalDenied('Authenticated identity and employee region are required')
    if not isinstance(question, str) or not question.strip() or len(question.encode('utf-8')) > MAX_QUESTION_BYTES:
        raise ValueError('Question is empty or oversized')
    if not isinstance(documents, list) or len(documents) > MAX_DOCUMENTS:
        raise ValueError('The bounded collection limit was exceeded')
    query = terms(question)
    ranked = []
    identifiers = set()
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError('Invalid document record')
        # Filter before inspecting titles/text or computing relevance. No denied
        # title, score, count, identifier or snippet enters the result.
        if document.get('sourceId') is not None:
            expiry = document.get('authorizationExpiresAt')
            if not isinstance(expiry, (int, float, Decimal)) or not math.isfinite(float(expiry)) or expiry <= time.time() or expiry > time.time() + 300:
                continue
        allowed = document.get('allowedSubjects')
        regions = document.get('allowedRegions')
        if not isinstance(allowed, list) or not isinstance(regions, list):
            continue
        if principal.subject not in allowed or principal.region not in regions:
            continue
        doc_id, revision = document.get('id'), document.get('revision')
        title, text = document.get('title'), document.get('text')
        if not all(isinstance(v, str) and v for v in [doc_id, revision, title, text]):
            raise ValueError('Invalid authorized document record')
        if doc_id in identifiers:
            raise ValueError('Duplicate document identity')
        identifiers.add(doc_id)
        if len(text.encode('utf-8')) > MAX_DOCUMENT_BYTES or len(title.encode('utf-8')) > 500:
            raise ValueError('Authorized document is oversized')
        overlap = len(query & terms(title + ' ' + text))
        if overlap:
            ranked.append((overlap, doc_id, {'id': doc_id, 'revision': revision, 'title': title, 'text': text}))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    result, size = [], 0
    for _, _, document in ranked[:MAX_RESULTS]:
        # Keep full evidence only. A silently truncated sentence could change meaning.
        amount = len((document['title'] + document['text']).encode('utf-8'))
        if size + amount > MAX_EVIDENCE_BYTES:
            continue
        result.append(document)
        size += amount
    return result


def validate_answer(response, evidence):
    """Validate citation membership, not truthfulness. Live quality eval is separate."""
    if not evidence:
        return {'answer': 'Insufficient evidence.', 'citations': [], 'abstained': True}
    if not isinstance(response, dict) or set(response) != {'answer', 'citations'}:
        raise ValueError('Invalid answer contract')
    answer, citations = response['answer'], response['citations']
    if not isinstance(answer, str) or not answer.strip() or len(answer.encode('utf-8')) > 16_000:
        raise ValueError('Invalid answer size')
    if answer == 'Insufficient evidence.' and citations == []:
        return {'answer': answer, 'citations': [], 'abstained': True}
    allowed = {item['id']: item for item in evidence}
    if not isinstance(citations, list) or not citations or not all(isinstance(c, str) for c in citations):
        raise ValueError('Evidence citations are required')
    if len(set(citations)) != len(citations) or any(c not in allowed for c in citations):
        raise ValueError('Unknown or repeated citation')
    return {'answer': answer, 'citations': [{'id': c, 'revision': allowed[c]['revision'], 'title': allowed[c]['title']} for c in citations], 'abstained': False}


def answer_question(question, principal, repository, generate, refresh_principal=None):
    """Recheck strongly consistent revisions/ACLs before generation and delivery.

    The repository adapter must fail closed on lookup errors and unknown identities.
    AWS adapters must supply refresh_principal to recheck identity status/region.
    No response cache is used. Revocation during generation suppresses delivery.
    """
    def verify_identity():
        if refresh_principal is not None and refresh_principal() != principal:
            raise RetrievalDenied('Identity authorization changed; retry the request')
    verify_identity()
    evidence = retrieve(question, repository.list_bounded(), principal)
    if not evidence:
        return validate_answer(None, [])
    def recheck():
        verify_identity()
        for item in evidence:
            current = repository.get_current(item['id'])
            visible = retrieve(question, [current] if current else [], principal)
            if not visible or visible[0] != item:
                raise RetrievalDenied('Authorization or evidence changed; retry the request')
    recheck()
    response = generate(question, evidence)
    recheck()
    return validate_answer(response, evidence)
