import {Extension, getSchema, Node} from '@tiptap/core';
import {StarterKit} from '@tiptap/starter-kit';
import {TableKit} from '@tiptap/extension-table';
import {Image} from '@tiptap/extension-image';
import {TextAlign} from '@tiptap/extension-text-align';
import {TextStyleKit} from '@tiptap/extension-text-style';

export const rasterData = value => typeof value === 'string' &&
  /^data:image\/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(value);
export const documentLink = value => typeof value === 'string' && /^(?:https?:\/\/|mailto:|#[a-z0-9])/i.test(value)
  && value.length <= 2048 && !/[\s\u0000-\u001f]/.test(value);
export const encodeRequirementBinding = (kind, id, field) => JSON.stringify([kind, id || '', field]);

export function decodeRequirementBinding(value) {
  if (typeof value !== 'string' || value.length > 350) return null;
  try {
    const data = JSON.parse(value);
    if (!Array.isArray(data) || data.length !== 3) return null;
    const [kind, id, field] = data;
    if (kind === 'scope' && id === '' && field === 'purpose') return {kind, field};
    if (kind === 'requirement' && typeof id === 'string' && id.length > 0 && id.length <= 100 &&
      ['statement','acceptance'].includes(field)) return {kind, id, field};
  } catch {}
  return null;
}

const DocumentAnchors = Extension.create({
  name: 'requirementsAnchors',
  addGlobalAttributes() {
    return [
      {types: ['paragraph', 'heading'], attributes: {requirementBinding: {
        default: null, keepOnSplit: false,
        parseHTML: element => {
          const value = element.getAttribute('data-requirement-binding');
          return decodeRequirementBinding(value) ? value : null;
        },
        renderHTML: attrs => attrs.requirementBinding ? {'data-requirement-binding': attrs.requirementBinding} : {},
      }}},
      {types: ['heading'], attributes: {documentAnchor: {
        default: null, keepOnSplit: false, parseHTML: () => null,
        renderHTML: attrs => attrs.documentAnchor ? {id: attrs.documentAnchor, tabindex: '-1'} : {},
      }}},
    ];
  },
});

const LocalImage = Image.extend({
  parseHTML() {
    return [{tag: 'img[src]', getAttrs: element => rasterData(element.getAttribute('src')) ? {} : false}];
  },
});

export const requirementsEditorExtensions = [
  StarterKit.configure({link: {isAllowedUri: documentLink, openOnClick: false, autolink: false, linkOnPaste: false}, trailingNode: false}),
  DocumentAnchors,
  TableKit.configure({table: {resizable: true}}),
  LocalImage.configure({allowBase64: true}),
  TextAlign.configure({types: ['heading', 'paragraph']}),
  TextStyleKit,
];

const WorkspaceDocument = Node.create({name: 'doc', topNode: true, content: 'requirementsPage+'});
const WorkspacePage = Node.create({
  name: 'requirementsPage',
  content: 'block+',
  defining: true,
  isolating: true,
  addAttributes() {
    return {pageId: {default: null, parseHTML: element => element.getAttribute('data-page-id')}};
  },
  parseHTML() {return [{tag: 'section[data-page-id]'}];},
  renderHTML({node}) {
    return ['section', {class: 'requirements-word-page', 'data-page-id': node.attrs.pageId || ''}, 0];
  },
});

export const requirementsWorkspaceExtensions = [
  requirementsEditorExtensions[0].configure({document: false}), WorkspaceDocument, WorkspacePage,
  ...requirementsEditorExtensions.slice(1),
];

export function newDocumentPage() {
  return {type: 'requirementsPage', attrs: {pageId: `page-${crypto.randomUUID()}`}, content: [
    {type: 'heading', attrs: {level: 2}, content: [{type: 'text', text: 'New page'}]}, {type: 'paragraph'},
  ]};
}

const schema = getSchema(requirementsEditorExtensions);
const boundedText = value => typeof value === 'string' && value.length <= 1000;
const positiveNumber = value => (typeof value === 'number' || typeof value === 'string') &&
  /^\d+(?:\.\d+)?$/.test(String(value)) && Number(value) > 0 && Number(value) <= 10000;
const color = value => typeof value === 'string' && /^(?:#[\da-f]{3,8}|[a-z]{1,25}|rgba?\([\d.,% /]+\)|hsla?\([\d.,% /]+\))$/i.test(value);
const attrs = {
  requirementBinding: value => !!decodeRequirementBinding(value),
  documentAnchor: value => typeof value === 'string' && /^req-rich-[a-z0-9-]{1,140}$/i.test(value),
  textAlign: value => ['left','right','center','justify'].includes(value),
  level: value => Number.isInteger(value) && value >= 1 && value <= 6,
  src: rasterData, alt: boundedText, title: boundedText,
  width: positiveNumber, height: positiveNumber,
  href: documentLink, target: value => ['_blank','_self'].includes(value),
  rel: value => typeof value === 'string' && /^[a-z ]{1,80}$/.test(value),
  language: value => typeof value === 'string' && /^[a-z0-9_+-]{1,40}$/i.test(value),
  start: positiveNumber, type: value => ['1','a','A','i','I'].includes(value),
  colspan: value => Number.isInteger(value) && value > 0 && value <= 100,
  rowspan: value => Number.isInteger(value) && value > 0 && value <= 100,
  colwidth: value => Array.isArray(value) && value.length <= 100 && value.every(width => width === 0 || positiveNumber(width)),
  color, backgroundColor: color,
  fontFamily: value => typeof value === 'string' && /^[a-z\d ,'"-]{1,100}$/i.test(value),
  fontSize: value => typeof value === 'string' && /^\d+(?:\.\d+)?(?:px|pt|rem|em|%)$/.test(value),
  lineHeight: value => (typeof value === 'string' || typeof value === 'number') && /^\d+(?:\.\d+)?(?:px|pt|rem|em|%)?$/.test(String(value)),
};

function cleanAttrs(entry, declaration) {
  return Object.fromEntries(Object.entries(entry.attrs || {}).filter(([key, value]) =>
    Object.hasOwn(declaration, key) && (value === null || !!attrs[key]?.(value))));
}

export function cleanRichDocument(content) {
  function sanitize(entry, depth = 0) {
    if (!entry || depth > 64 || !Object.hasOwn(schema.nodes, entry.type)) throw Error('Invalid document structure.');
    const result = {type: entry.type, attrs: cleanAttrs(entry, schema.nodes[entry.type].attrs)};
    if (entry.type === 'image' && !rasterData(result.attrs.src)) throw Error('Insert a local PNG, JPEG, GIF or WebP image.');
    if (entry.type === 'text') {
      if (typeof entry.text !== 'string' || !entry.text) throw Error('Invalid document text.');
      result.text = entry.text;
    }
    if (entry.marks) {
      if (!Array.isArray(entry.marks)) throw Error('Invalid document formatting.');
      result.marks = entry.marks.flatMap(mark => {
        if (!mark || !Object.hasOwn(schema.marks, mark.type)) throw Error('Invalid document formatting.');
        const attributes = cleanAttrs(mark, schema.marks[mark.type].attrs);
        if (mark.type === 'link') {
          if (!documentLink(attributes.href)) return [];
          attributes.rel = 'noopener noreferrer';
        }
        return [{type: mark.type, attrs: attributes}];
      });
    }
    if (entry.content) {
      if (!Array.isArray(entry.content)) throw Error('Invalid document content.');
      result.content = entry.content.map(child => sanitize(child, depth + 1));
    }
    return result;
  }
  if (content?.type !== 'doc') throw Error('Invalid document page.');
  const node = schema.nodeFromJSON(sanitize(content));
  node.check();
  return node.toJSON();
}

export function documentText(node) {
  if (node.type === 'hardBreak') return '\n';
  return node.text || (node.content || []).map(documentText).join('');
}

export function mapDocumentNodes(node, visit) {
  return visit(node.content ? {...node, content: node.content.map(child => mapDocumentNodes(child, visit))} : node);
}

export function richHeadings(doc) {
  return (doc.content || []).filter(node => node.type === 'heading').map(node => ({
    id: node.attrs?.documentAnchor, text: documentText(node).trim(), level: node.attrs?.level,
  })).filter(heading => heading.text);
}

export function numberRichHeadings(doc, page) {
  let index = 0;
  return mapDocumentNodes(doc, node => node.type === 'heading'
    ? {...node, attrs: {...node.attrs, documentAnchor: `req-rich-${page}-${++index}`}} : node);
}
