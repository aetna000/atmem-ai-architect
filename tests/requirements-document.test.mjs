import assert from 'node:assert/strict';
import {test} from 'node:test';
import {fromProjectFile, toProjectFile} from '../src/project-file.mjs';
import {documentState, updateRequirementsDocument} from '../src/requirements-document.mjs';

const seed = () => ({
  version: 1, revision: 1, id: 'requirements-editor-test', name: 'Warehouse controls', provider: 'tools',
  requirements: 'Process warehouse orders.', nodes: [], edges: [],
  needs: [{id: 'order-intake', kind: 'functional', source: 'user', statement: 'Receive an order.'}],
});
const statement = {kind: 'requirement', id: 'order-intake', field: 'statement'};
const table = {id: 'table-1', page: 'scope', kind: 'table', rows: [['Source', 'Destination'], ['API', 'Worker']]};

test('pending text and table changes survive project export and only acceptance changes the document', () => {
  let project = updateRequirementsDocument(seed(), {type: 'tracking', enabled: true});
  project = updateRequirementsDocument(project, {type: 'edit', target: statement, before: 'Receive an order.', after: 'Validate each order.'});
  project = updateRequirementsDocument(project, {type: 'edit', target: {kind: 'block', id: table.id}, before: null, after: table});
  project = fromProjectFile(toProjectFile(project)).project;
  assert.equal(project.needs[0].statement, 'Receive an order.');
  assert.deepEqual(documentState(project).blocks, []);
  const [edit, insert] = documentState(project).changes;
  project = updateRequirementsDocument(project, {type: 'decide', id: edit.id, accept: false});
  project = updateRequirementsDocument(project, {type: 'decide', id: insert.id, accept: true});
  assert.equal(project.needs[0].statement, 'Receive an order.');
  assert.deepEqual(documentState(project).blocks, [table]);
  assert.deepEqual(documentState(project).changes, []);
});

test('thread replies keep their anchor and stale tracked changes cannot overwrite newer wording', () => {
  let project = updateRequirementsDocument(seed(), {type: 'comment', anchor: 'page:scope', text: 'Confirm owner.'});
  const [thread] = documentState(project).threads;
  project = updateRequirementsDocument(project, {type: 'reply', id: thread.id, text: 'Warehouse operations.'});
  project = updateRequirementsDocument(project, {type: 'tracking', enabled: true});
  project = updateRequirementsDocument(project, {type: 'edit', target: statement, before: 'Receive an order.', after: 'Reject duplicates.'});
  const [draft] = documentState(project).changes;
  project = {...project, needs: [{...project.needs[0], statement: 'Receive a purchase order.'}]};
  assert.throws(() => updateRequirementsDocument(project, {type: 'decide', id: draft.id, accept: true}), /stale change/);
  const reloaded = fromProjectFile(toProjectFile(project)).project;
  assert.equal(documentState(reloaded).threads[0].anchor, 'page:scope');
  assert.equal(documentState(reloaded).threads[0].replies[0].text, 'Warehouse operations.');
});

test('import rejects document image URLs that are not embedded raster data', () => {
  const exported = toProjectFile(seed());
  exported.extensions.requirementsDocument = {
    tracking: false, changes: [], threads: [],
    blocks: [{id: 'image-1', page: 'scope', kind: 'image', image: 'https://example.com/image.png', alt: 'Remote image'}],
  };
  assert.throws(() => fromProjectFile(exported), /Invalid requirements document data/);
});

test('rich page review preserves formatting and updates linked requirement text only on acceptance', async () => {
  const {encodeRequirementBinding} = await import('../src/requirements-rich-document.mjs');
  const {richBindingBasis, richPage} = await import('../src/requirements-document.mjs');
  const key = encodeRequirementBinding('requirement', 'order-intake', 'statement');
  const page = (text, marks) => ({type: 'doc', content: [
    {type: 'heading', attrs: {level: 2}, content: [{type: 'text', text: 'Order intake'}]},
    {type: 'paragraph', attrs: {requirementBinding: key}, content: [{type: 'text', text, marks}]},
  ]});
  let project = updateRequirementsDocument(seed(), {type: 'tracking', enabled: true});
  const previous = page('Receive an order.');
  project = updateRequirementsDocument(project, {type: 'editPage', id: 'requirements-functional',
    before: null, previous, content: page('Validate each order.', [{type: 'bold'}]), bindings: richBindingBasis(project, previous)});
  project = fromProjectFile(toProjectFile(project)).project;
  assert.equal(project.needs[0].statement, 'Receive an order.');
  assert.equal(richPage(project, 'requirements-functional'), null);
  const [change] = documentState(project).changes;
  const modified = {...project, needs: [{...project.needs[0], statement: 'Receive a revised order.'}]};
  assert.throws(() => updateRequirementsDocument(modified, {type: 'decide', id: change.id, accept: true}), /linked requirement changed/);
  project = updateRequirementsDocument(project, {type: 'decide', id: change.id, accept: true});
  assert.equal(project.needs[0].statement, 'Validate each order.');
  const accepted = richPage(project, 'requirements-functional');
  assert.equal(accepted.doc.content[1].content[0].marks[0].type, 'bold');
  assert.match(accepted.doc.content[0].attrs.documentAnchor, /^req-rich-/);
});

test('rich documents sanitize links and CSS and require embedded raster image data', async () => {
  const {cleanRichDocument} = await import('../src/requirements-rich-document.mjs');
  const doc = {type: 'doc', content: [{type: 'paragraph', content: [
    {type: 'text', text: 'Example', marks: [
      {type: 'link', attrs: {href: 'javascript:alert(1)'}},
      {type: 'textStyle', attrs: {fontFamily: 'serif; background:url(https://example.org/)', fontSize: '12pt'}},
    ]},
  ]}]};
  const marks = cleanRichDocument(doc).content[0].content[0].marks;
  assert.deepEqual(marks.map(mark => mark.type), ['textStyle']);
  assert.equal(marks[0].attrs.fontFamily, null);
  assert.equal(marks[0].attrs.fontSize, '12pt');
  assert.throws(() => cleanRichDocument({type: 'doc', content: [{type: 'image', attrs: {src: 'https://example.org/picture.png'}}]}), /local PNG/);
});
