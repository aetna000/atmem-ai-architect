"""Bounded diagram authoring using the application's selected model connection."""
import asyncio
import json
from typing import Annotated, Literal

from pydantic import Field, ValidationError

from .attachments import prepare
from .contracts import Attachment, ChatRequest, Strict
from .local_providers import call_cli
from .diagram_quality import review

from .diagram_skills import CATALOGUE, FIELDS, SKILLS, SYSTEM, TYPES

Id = Annotated[str, Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_-]{0,95}$')]
Name = Annotated[str, Field(min_length=1, max_length=180)]


class DiagramRequest(Strict):
    provider: ChatRequest.model_fields['provider'].annotation
    model: str = Field(min_length=1, max_length=150)
    effort: ChatRequest.model_fields['effort'].annotation = None
    specification: str = Field(default='', max_length=160_000)
    projectContext: str = Field(default='', max_length=1_200_000)
    attachments: list[Attachment] = Field(default_factory=list, max_length=2)
    resume: dict | None = None


class Detail(Strict):
    name: str = Field(min_length=1, max_length=48)
    value: str = Field(min_length=1, max_length=1600)


class Record(Strict):
    id: Id
    name: Name
    kind: str = Field(min_length=1, max_length=48)
    basis: Literal['specified', 'proposed', 'manual', 'example']
    source: str = Field(max_length=500)
    details: list[Detail] = Field(max_length=16)


class Element(Record):
    parentId: Id | None = None


class Relation(Record):
    fromId: Id
    toId: Id


class GroupMembership(Strict):
    elementId: Id
    groupId: Id


class View(Strict):
    id: Id
    name: Name
    kind: str = Field(min_length=1, max_length=48)
    scopeId: Id | None = None
    groups: list[GroupMembership] | None = Field(default=None,max_length=80)
    elementIds: list[Id] = Field(max_length=80)
    relationIds: list[Id] = Field(max_length=180)
    gaps: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(max_length=600)


class Proposal(Strict):
    version: Literal[1]
    elements: list[Element] = Field(max_length=650)
    relations: list[Relation] = Field(max_length=900)
    views: list[View] = Field(min_length=1, max_length=len(TYPES))


def validate(raw, expected=None, existing=None):
    proposal = Proposal.model_validate(raw)
    existing = existing or {'elements': [], 'relations': [], 'views': []}
    new_rows = [*proposal.elements, *proposal.relations, *proposal.views]
    rows = [*existing['elements'], *existing['relations'], *existing['views'], *new_rows]
    elements = {row.id: row for row in [*existing['elements'], *proposal.elements]}
    relations = {row.id: row for row in [*existing['relations'], *proposal.relations]}
    if len(elements) > 650 or len(relations) > 900:
        raise ValueError('Keep the complete model within 650 shared elements and 900 relationships.')
    if len({row.id for row in rows}) != len(rows):
        raise ValueError('Use unique IDs across all records and views.')
    if any(not row.name.strip() or row.id == 'constructor' for row in rows):
        raise ValueError('Use safe IDs and nonblank names.')
    expected = set(expected or TYPES)
    if {row.kind for row in proposal.views} != expected or len(proposal.views) != len(expected):
        raise ValueError('Return each requested diagram type exactly once.')
    for collection, category in [(proposal.elements, 'elements'), (proposal.relations, 'relations')]:
        kinds = {kind for type_ in CATALOGUE for kind in type_[category]}
        for row in collection:
            if row.kind not in kinds or row.basis == 'specified' and not row.source.strip():
                raise ValueError(f'{row.id} needs a supported kind and a source for specified records.')
            names = {detail.name.casefold().strip() for detail in row.details}
            if '' in names or len(names) != len(row.details) or any(not detail.value.strip() for detail in row.details):
                raise ValueError(f'{row.id} has blank or duplicate notation fields.')
    for row in proposal.elements:
        seen = {row.id}
        parent = row.parentId
        while parent:
            if parent in seen or parent not in elements:
                raise ValueError(f'{row.id} has a missing parent or ownership cycle.')
            seen.add(parent)
            parent = elements[parent].parentId
    for row in proposal.relations:
        if row.fromId not in elements or row.toId not in elements:
            raise ValueError(f'{row.id} needs existing endpoints.')
    for view in proposal.views:
        type_ = TYPES[view.kind]
        visible = set(view.elementIds)
        if (len(visible) != len(view.elementIds) or (view.scopeId and view.scopeId not in visible)
            or any(element not in elements or elements[element].kind not in type_['elements'] for element in visible)):
            raise ValueError(f'{view.kind} has an invalid scope or visible element.')
        memberships = {row.elementId: row.groupId for row in (view.groups or [])}
        if len(memberships) != len(view.groups or []) or (memberships.keys() | set(memberships.values())) - visible:
            raise ValueError(f'{view.kind} has an invalid group membership.')
        for ident in memberships:
            seen = set()
            while ident in visible:
                if ident in seen:
                    raise ValueError(f'{view.kind} has a group membership cycle.')
                seen.add(ident)
                ident = memberships.get(ident) or elements[ident].parentId
        if not visible and not view.gaps:
            raise ValueError(f'{view.kind} needs an explanation for its empty scope.')
        if type_['layout'] != 'timeline' and len(set(view.relationIds)) != len(view.relationIds):
            raise ValueError(f'{view.kind} has a repeated relationship.')
        for ident in view.relationIds:
            edge = relations.get(ident)
            if not edge or edge.kind not in type_['relations'] or {edge.fromId, edge.toId} - visible:
                raise ValueError(f'{view.kind} contains an incompatible relationship or hidden endpoint.')
    return proposal


async def draft(architect, request, disconnected, progress=None):
    attached = await asyncio.to_thread(prepare, [row.model_dump() for row in request.attachments], design=True)
    sources = [{key: row[key] for key in ('name', 'text', 'mode', 'graphics') if key in row} for row in attached]
    size = len(request.specification) + len(request.projectContext) + sum(len(row.get('text', '')) for row in sources)
    if size > 1_250_000:
        raise ValueError('The combined specification and project context exceed 1,250,000 characters.')
    if not (request.specification.strip() or request.projectContext.strip() or sources):
        raise ValueError('Add a solution specification or project requirements.')
    groups = list(dict.fromkeys(row['group'] for row in CATALOGUE))
    accumulated = {'elements': [], 'relations': [], 'views': []}
    if request.resume:
        saved = json.loads(json.dumps(request.resume))
        for row in saved.get('relations', []):
            row['fromId'] = row.pop('from')
            row['toId'] = row.pop('to')
        restored = validate(saved, [view['kind'] for view in saved.get('views', [])])
        accumulated = {key:list(getattr(restored,key)) for key in accumulated}
    system = SYSTEM + ('\nUse fromId and toId for relationship endpoints. Project context is JSON encoded as text.'
                       ' Embedded figures were not interpreted. Treat them as evidence gaps when relevant.'
                       ' Never re-emit an existingModel record. Refer to its ID only.'
                       ' Earlier accepted records in projectContext may be re-emitted if reused; keep their kind, endpoints and ownership.')
    base = {'specification': request.specification, 'projectContext': request.projectContext,
            'attachedEvidence': sources}
    native = request.provider in {'claude-code', 'codex', 'copilot', 'gemini-cli'}
    if not native:
        system += '\nThe JSON schema is included in the request. Respond with a single JSON object.'

    async def author_group(group, rows):
        active = [{**{key: value for key, value in row.items() if key != 'starter'}, 'skill': SKILLS[row['id']]}
                  for row in rows]
        if progress:
            await progress({'group': group, 'done': len(accumulated['views']), 'total': len(CATALOGUE)})
        kinds = [row['id'] for row in active]
        schema = Proposal.model_json_schema()
        schema['$defs']['View']['properties']['kind']['enum'] = kinds
        schema['properties']['views'].update(minItems=len(kinds), maxItems=len(kinds))
        payload = {**base, 'catalogue': active, 'requiredViewKinds': kinds,
                   **({'outputSchema': schema} if not native else {}),
                   'notationFields': {key: {kind: fields for kind, fields in values.items() if any(kind in row['elements' if key=='elementFields' else 'relations'] for row in active)} for key, values in FIELDS.items()},
                   'existingModel': {key: [row.model_dump(include={'id','kind','name','fromId','toId','parentId'}, exclude_none=True) for row in value] for key, value in accumulated.items()}}
        best = None
        retained_source_records = set()
        timed_out = False
        for attempt in range(2):
            if await disconnected():
                raise asyncio.CancelledError()
            prompt = json.dumps(payload, ensure_ascii=False)
            try:
                if native:
                    raw = await call_cli(request.provider, request.model, prompt, system, schema,
                                         disconnected, request.effort, timeout=240 if attempt==0 else 150)
                else:
                    async with architect._sdk_lock:
                        raw = await asyncio.wait_for(asyncio.to_thread(
                            architect._strands, request, prompt=prompt, system=system, max_tokens=16000), timeout=180)
                proposal = validate(raw, kinds, accumulated)
            except TimeoutError:
                timed_out = True
                break
            except (ValidationError, ValueError) as error:
                payload['repair'] = (error.errors(include_input=False, include_url=False)[:12]
                                     if isinstance(error, ValidationError) else str(error))
                continue

            elements = {row.id: row for row in [*accumulated['elements'], *proposal.elements]}
            relations = {row.id: row for row in [*accumulated['relations'], *proposal.relations]}
            findings = review(proposal.views, elements, relations, SKILLS)
            count = sum(map(len, findings.values()))
            score = (sum(not view.elementIds for view in proposal.views), count,
                     -sum(len(view.elementIds)+len(view.relationIds) for view in proposal.views))
            visible = {ident for view in proposal.views for ident in [*view.elementIds, *view.relationIds]}
            source_records = {(row.kind, row.name, row.source) for ident, row in {**elements, **relations}.items()
                              if ident in visible and row.basis=='specified'}
            if best is None or (score <= best[0] and retained_source_records <= source_records):
                best = (score, proposal, findings)
                retained_source_records = source_records
            # An evidence gap is an actionable result. Try once to resolve checklist
            # findings using the same source and keep valid coverage after that pass.
            if not count and not score[0] and best[1] is proposal:
                break
            payload['review'] = {kind: issues for kind, issues in findings.items() if issues}
            payload['repairInstruction'] = ('Repair every finding supported by the supplied evidence. Preserve the '
                                            'existing records and substantive details. Keep unresolved items with their '
                                            'owner and the concrete evidence needed to close them.')
            for view in proposal.views:
                if not view.elementIds:
                    payload['review'][view.kind] = ['Try to produce a useful, evidence-backed projection or retain the specific scope gap.']
            payload['previousDraft'] = proposal.model_dump(exclude_none=True)
            payload.pop('repair', None)

        if best is None:
            if len(rows)>1:
                middle = len(rows)//2
                await author_group(group, rows[:middle])
                await author_group(group, rows[middle:])
                return
            if timed_out:
                raise TimeoutError(f'{rows[0]["title"]} timed out.')
            raise RuntimeError(f'AtMem could not validate {rows[0]["title"]} after two attempts.')
        _, proposal, findings = best
        for view in proposal.views:
            view.gaps = list(dict.fromkeys([*view.gaps, *findings[view.kind]]))
        for key, records in accumulated.items():
            records.extend(getattr(proposal, key))
        if progress:
            checkpoint = Proposal(version=1, **accumulated).model_dump(exclude_none=True)
            for row in checkpoint['relations']:
                row['from'] = row.pop('fromId')
                row['to'] = row.pop('toId')
            await progress({'group': group, 'done': len(accumulated['views']), 'total': len(CATALOGUE), 'checkpoint': checkpoint})
    for group in groups:
        rows = [row for row in CATALOGUE if row['group'] == group and row['id'] not in {view.kind for view in accumulated['views']}]
        batch_size = 1 if size >= 40_000 else max(1,len(rows))
        for offset in range(0, len(rows), batch_size):
            await author_group(group, rows[offset:offset+batch_size])
    proposal = Proposal(version=1, **accumulated)
    validate(proposal.model_dump())
    result = proposal.model_dump(exclude_none=True)
    for row in result['relations']:
        row['from'] = row.pop('fromId')
        row['to'] = row.pop('toId')
    return result
