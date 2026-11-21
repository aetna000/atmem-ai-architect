import {recordedOutcome} from './source-scope.mjs';
import {cleanRichDocument, decodeRequirementBinding, documentText, mapDocumentNodes, numberRichHeadings, rasterData} from './requirements-rich-document.mjs';

const extension = 'requirementsDocument';
const empty = {tracking: false, blocks: [], changes: [], threads: []};
const textFields = {requirement: ['statement', 'acceptance'], scope: ['purpose']};

export const documentState = project => project.extensions?.[extension] || empty;
export const supportedImage = rasterData;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const targetKey = target => [target.kind, target.id, target.field].join(':');
const validText = (value, limit) => typeof value === 'string' && value.length <= limit;
const validId = value => typeof value === 'string' && /^[a-z0-9-]{1,100}$/i.test(value);

export function validDocumentBlock(block, id) {
  if (!block || block.id !== id || !validId(id) || !validId(block.page)) return false;
  switch (block.kind) {
    case 'text': return validText(block.text, 20_000) && Boolean(block.text.trim()) && ['paragraph', 'heading'].includes(block.style);
    case 'image': return supportedImage(block.image) && validText(block.alt, 1000) && Boolean(block.alt.trim());
    case 'table': return Array.isArray(block.rows) && block.rows.length >= 2 && block.rows.length <= 100 &&
      Array.isArray(block.rows[0]) && block.rows[0].length >= 1 && block.rows[0].length <= 20 &&
      block.rows.every(row => Array.isArray(row) && row.length === block.rows[0].length && row.every(value => validText(value, 4000)));
    default: return false;
  }
}

export function documentValue(project, target) {
  if (target.kind === 'block') return documentState(project).blocks.find(block => block.id === target.id) || null;
  if (!Object.hasOwn(textFields, target.kind) || !textFields[target.kind].includes(target.field)) throw Error('This document field is unavailable.');
  if (target.kind === 'scope') return recordedOutcome(project);
  const row = project.needs?.find(requirement => requirement.id === target.id);
  if (!row) throw Error('This requirement was removed.');
  return row[target.field] || '';
}

function validateEdit(project, target, value) {
  if (target.kind === 'block') {
    if (value !== null && !validDocumentBlock(value, target.id)) throw Error('Complete the text, table or image details.');
  } else if (!validText(value, target.kind === 'requirement' ? 1000 : project.brief?.application ? 2000 : 64_000) ||
    (target.field !== 'acceptance' && !value.trim())) throw Error('Enter valid document text within the field limit.');
}

function apply(project, state, target, value) {
  if (target.kind === 'block') {
    const exists = state.blocks.some(block => block.id === target.id);
    const blocks = exists ? state.blocks.flatMap(block => block.id === target.id ? value ? [value] : [] : [block]) : [...state.blocks, value];
    return [project, {...state, blocks}];
  }
  if (target.kind === 'scope') {
    return [project.brief?.application
      ? {...project, brief: {...project.brief, application: value}}
      : {...project, requirements: value}, state];
  }
  const needs = project.needs.map(row => row.id === target.id
    ? {...row, [target.field]: value, ...(row.source === 'agent' && row.id.startsWith('drv-') ? {source: 'user'} : {})} : row);
  return [{...project, needs}, state];
}

export const richPage = (project, id) => documentState(project).richPages?.find(page => page.id === id) || null;

function documentBindings(doc) {
  const values = new Map();
  mapDocumentNodes(doc, node => {
    const key = node.attrs?.requirementBinding;
    if (key && !values.has(key)) values.set(key, documentText(node));
    return node;
  });
  return values;
}

export function richBindingBasis(project, doc) {
  return [...documentBindings(doc).keys()].map(key => [key, documentValue(project, decodeRequirementBinding(key))]);
}

export function refreshRichBindings(project, doc) {
  return mapDocumentNodes(doc, node => {
    const key = node.attrs?.requirementBinding;
    if (!key) return node;
    const binding = decodeRequirementBinding(key);
    if (!binding) return node;
    if (binding.kind === 'requirement' && !project.needs?.some(row => row.id === binding.id)) {
      return {...node, attrs: {...node.attrs, requirementBinding: null}};
    }
    const value = documentValue(project, binding);
    if (value === documentText(node)) return node;
    const marks = node.content?.find(child => child.type === 'text')?.marks;
    const content = value.split('\n').flatMap((line, index) => [
      ...(index ? [{type: 'hardBreak'}] : []), ...(line ? [{type: 'text', text: line, ...(marks ? {marks} : {})}] : []),
    ]);
    return {...node, content};
  });
}

function applyRichPage(project, state, page, fields) {
  let next = project;
  for (const {key, before, after} of fields) {
    const target = decodeRequirementBinding(key);
    if (documentValue(next, target) !== before) throw Error('A linked requirement changed. Review its latest wording before saving.');
    validateEdit(next, target, after);
    [next] = apply(next, state, target, after);
  }
  const pages = state.richPages || [];
  const updated = pages.some(row => row.id === page.id) ? pages.map(row => row.id === page.id ? page : row) : [...pages, page];
  return [next, {...state, richPages: updated}];
}

function prepareRichChange(project, state, {id, before, previous, content, bindings, hidden}) {
  if (!validId(id)) throw Error('Invalid document page.');
  if (!same(richPage(project, id), before)) throw Error('This page changed while you were editing. Reopen it.');
  if (state.changes.some(row => row.target.kind === 'richPage' && row.target.id === id)) throw Error('Review the pending page change first.');
  const original = cleanRichDocument(previous);
  const oldFields = documentBindings(original);
  const baseline = new Map(bindings);
  const seen = new Set();
  const safe = mapDocumentNodes(cleanRichDocument(content), node => {
    const key = node.attrs?.requirementBinding;
    if (!key) return node;
    if (!oldFields.has(key)) return {...node, attrs: {...node.attrs, requirementBinding: null}};
    if (seen.has(key)) throw Error('A linked requirement was duplicated. Remove the copied paragraph and paste as plain text.');
    seen.add(key);
    return node;
  });
  const after = {id, doc: numberRichHeadings(safe, id), ...(hidden ? {hidden: true} : {})};
  const fields = [...documentBindings(safe)].flatMap(([key, value]) => {
    if (oldFields.get(key) === value) return [];
    const target = decodeRequirementBinding(key);
    const sourceValue = baseline.get(key);
    if (documentValue(project, target) !== sourceValue) throw Error('A linked requirement changed. Reopen this page to review the latest text.');
    validateEdit(project, target, value);
    if (state.changes.some(row => targetKey(row.target) === targetKey(target))) throw Error('Review the pending change for this requirement first.');
    return [{key, before: sourceValue, after: value}];
  });
  return {id: crypto.randomUUID(), target: {kind: 'richPage', id}, before, previous: original, after, fields};
}

export function updateRequirementsDocument(project, command) {
  let state = documentState(project);
  let next = project;
  switch (command.type) {
    case 'tracking':
      state = {...state, tracking: Boolean(command.enabled)};
      break;
    case 'edit': {
      const {target, before, after} = command;
      const current = documentValue(project, target);
      if (same(current, after)) return project;
      if (!same(current, before)) throw Error('This text changed while you were editing. Reopen the editor.');
      validateEdit(project, target, after);
      const existing = state.changes.find(change => targetKey(change.target) === targetKey(target));
      if (existing) throw Error('Review the pending change for this item first.');
      if (state.tracking) {
        state = {...state, changes: [...state.changes, {id: crypto.randomUUID(), target, before, after}]};
      } else {
        [next, state] = apply(project, state, target, after);
      }
      break;
    }
    case 'editPages':
      return command.entries.reduce((current, entry) => updateRequirementsDocument(current, {...entry, type: 'editPage'}), project);
    case 'editPage': {
      const change = prepareRichChange(project, state, command);
      if (state.tracking) state = {...state, changes: [...state.changes, change]};
      else [next, state] = applyRichPage(project, state, change.after, change.fields);
      break;
    }
    case 'decide': {
      const change = state.changes.find(item => item.id === command.id);
      if (!change) throw Error('This change is no longer pending.');
      if (command.accept && change.target.kind === 'richPage') {
        if (!same(richPage(project, change.target.id), change.before)) throw Error('This page changed after review began.');
        [next, state] = applyRichPage(project, state, change.after, change.fields);
      } else if (command.accept) {
        if (!same(documentValue(project, change.target), change.before)) throw Error('This item changed since review began. Reject the stale change and edit again.');
        validateEdit(project, change.target, change.after);
        [next, state] = apply(project, state, change.target, change.after);
      }
      state = {...state, changes: state.changes.filter(item => item.id !== command.id)};
      break;
    }
    case 'comment':
    case 'reply': {
      const text = command.text.trim();
      if (!text || text.length > 1800) throw Error('Enter up to 1,800 characters.');
      const message = {id: crypto.randomUUID(), text, createdAt: new Date().toISOString()};
      if (command.type === 'comment') {
        state = {...state, threads: [...state.threads, {...message, anchor: command.anchor, ...(command.quote ? {quote: String(command.quote).slice(0, 1500)} : {}), replies: []}]};
      } else {
        if (!state.threads.some(thread => thread.id === command.id)) throw Error('This comment is no longer available.');
        state = {...state, threads: state.threads.map(thread => thread.id === command.id
          ? {...thread, replies: [...thread.replies, message]} : thread)};
      }
      break;
    }
    default: throw Error('Unknown document action.');
  }
  return {...next, extensions: {...next.extensions, [extension]: state}};
}

export function validateRequirementsDocument(state) {
  if (state === undefined) return;
  const validMessage = message => validId(message?.id) && validText(message.text, 1800) && Boolean(message.text.trim());
  const validPage = (page, id) => {
    if (!page || page.id !== id || !validId(id) || (page.hidden !== undefined && typeof page.hidden !== 'boolean')) return false;
    cleanRichDocument(page.doc);
    return true;
  };
  const validChange = item => {
    if (!validId(item?.id) || !item.target) return false;
    const {target, before, after} = item;
    if (target.kind === 'richPage') {
      cleanRichDocument(item.previous);
      return (before === null || validPage(before, target.id)) && validPage(after, target.id) &&
        Array.isArray(item.fields) && item.fields.every(field => field && decodeRequirementBinding(field.key) &&
          validText(field.before, 64_000) && validText(field.after, 64_000)) && unique(item.fields, field => field.key);
    }
    if (target.kind === 'block') {
      return validId(target.id) && (before === null || validDocumentBlock(before, target.id)) &&
        (after === null || validDocumentBlock(after, target.id)) && (before !== null || after !== null);
    }
    return Object.hasOwn(textFields, target.kind) && textFields[target.kind].includes(target.field) &&
      (target.kind !== 'requirement' || validText(target.id, 100)) &&
      validText(before, 64_000) && validText(after, 64_000);
  };
  const unique = (rows, identify) => new Set(rows.map(identify)).size === rows.length;
  if (!state || typeof state.tracking !== 'boolean' ||
    (state.richPages !== undefined && (!Array.isArray(state.richPages) || !state.richPages.every(page => validPage(page, page?.id)) || !unique(state.richPages, page => page.id))) ||
    !Array.isArray(state.blocks) || !state.blocks.every(block => validDocumentBlock(block, block?.id)) || !unique(state.blocks, block => block.id) ||
    !Array.isArray(state.changes) || !state.changes.every(validChange) || !unique(state.changes, row => row.id) || !unique(state.changes, row => targetKey(row.target)) ||
    !Array.isArray(state.threads) || !state.threads.every(thread => validMessage(thread) && validText(thread.anchor, 180) && (thread.quote === undefined || validText(thread.quote, 1500)) &&
      Array.isArray(thread.replies) && thread.replies.every(validMessage) && unique(thread.replies, reply => reply.id)) ||
    !unique(state.threads, thread => thread.id)) throw Error('Invalid requirements document data.');
}
