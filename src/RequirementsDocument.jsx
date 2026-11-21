import React, {useEffect, useRef, useState} from 'react';
import {FilePenLine, ImagePlus, List, MessageSquare, Printer, Table2} from 'lucide-react';
import {documentState, refreshRichBindings, richBindingBasis, richPage, supportedImage, validDocumentBlock} from './requirements-document.mjs';
import {cleanRichDocument, newDocumentPage, richHeadings} from './requirements-rich-document.mjs';
import {RequirementsPageEditor, RichPagePreview, snapshotPage} from './RequirementsPageEditor.jsx';
import './requirements-document.css';

export function ReplyForm({onReply}) {
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  return <form className="requirements-reply" onSubmit={event => {
    event.preventDefault();
    try {onReply(text); setText(''); setError('');} catch (failure) {setError(failure.message);}
  }}>
    <input aria-label="Reply to comment" placeholder="Write a reply" maxLength={1800} value={text} onChange={event => setText(event.target.value)}/>
    <button type="submit" className="btn" disabled={!text.trim()}>Reply</button>
    {error && <span role="alert">{error}</span>}
  </form>;
}

export function DocumentThreads({threads, anchor, change, quote}) {
  const rows = threads.filter(thread => thread.anchor === anchor);
  return <details className="requirements-threads document-controls" open={quote ? true : undefined}>
    <summary><MessageSquare size={15}/> Comments{rows.length ? ` (${rows.length})` : ''}</summary>
    {rows.map(thread => <div className="requirements-thread" key={thread.id}>
      {thread.quote && <blockquote>{thread.quote}</blockquote>}
      <p>{thread.text}</p>
      {thread.replies.map(reply => <p key={reply.id} className="requirements-thread-reply">{reply.text}</p>)}
      <ReplyForm onReply={text => change({type: 'reply', id: thread.id, text})}/>
    </div>)}
    <CommentForm anchor={anchor} change={change} quote={quote}/>
  </details>;
}

function CommentForm({anchor, change, quote}) {
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  return <form onSubmit={event => {
    event.preventDefault();
    try {change({type: 'comment', anchor, text, quote}); setText(''); setError('');} catch (failure) {setError(failure.message);}
  }}>
    {quote && <blockquote>{quote}</blockquote>}
    <textarea aria-label="Document comment" rows={2} placeholder="Add a comment" maxLength={1800}
      value={text} onChange={event => setText(event.target.value)}/>
    <button type="submit" className="btn" disabled={!text.trim()}>Post comment</button>
    {error && <p role="alert">{error}</p>}
  </form>;
}

export function DocumentText({target, value, change, label, limit, children, pending}) {
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState('');
  return <div className="requirements-editable">
    {children}
    {!draft ? <button type="button" className="link document-controls" disabled={pending}
      onClick={() => setDraft({before: value, after: value})}>{label}</button> : (
      <form className="requirements-edit-form document-controls" onSubmit={event => {
        event.preventDefault();
        try {change({type: 'edit', target, ...draft}); setDraft(null); setError('');} catch (failure) {setError(failure.message);}
      }}>
        <textarea autoFocus aria-label={label} rows={4} maxLength={limit} value={draft.after}
          onChange={event => setDraft({...draft, after: event.target.value})}/>
        <button type="submit" className="btn">Save edit</button>{' '}
        <button type="button" className="link" onClick={() => {setDraft(null); setError('');}}>Cancel</button>
        {error && <p role="alert">{error}</p>}
      </form>
    )}
    {pending && <small className="document-controls">Change pending review</small>}
  </div>;
}

function BlockContent({block, linkable = false}) {
  if (!validDocumentBlock(block, block?.id)) return null;
  if (block.kind === 'image') return <figure><img src={block.image} alt={block.alt}/><figcaption>{block.alt}</figcaption></figure>;
  if (block.kind === 'table') return <div className="requirements-table-scroll"><table>
    <thead><tr>{block.rows[0].map((cell, index) => <th key={index} scope="col">{cell}</th>)}</tr></thead>
    <tbody>{block.rows.slice(1).map((row, index) => <tr key={index}>{row.map((cell, column) => <td key={column}>{cell}</td>)}</tr>)}</tbody>
  </table></div>;
  return block.style === 'heading' ? <h4 id={linkable ? `req-heading-${block.id}` : undefined} tabIndex={linkable ? -1 : undefined}>{block.text}</h4> : <p>{block.text}</p>;
}

function BlockEditor({original, initial, change, close}) {
  const [block, setBlock] = useState(initial);
  const [error, setError] = useState('');
  const [reading, setReading] = useState(false);
  const patch = values => setBlock(current => ({...current, ...values}));
  const commit = after => {
    try {change({type: 'edit', target: {kind: 'block', id: block.id}, before: original, after}); close();}
    catch (failure) {setError(failure.message);}
  };
  async function loadImage(file) {
    if (!file) return;
    setReading(true);
    try {
      const image = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(Error('Could not read the image.'));
        reader.onload = () => resolve(reader.result);
        reader.readAsDataURL(file);
      });
      if (!supportedImage(image)) throw Error('Choose a PNG, JPEG, GIF or WebP image.');
      const preview = new Image();
      preview.src = image;
      await preview.decode();
      patch({image});
      setError('');
    } catch (failure) {setError(failure.message || 'Could not decode the image.');}
    finally {setReading(false);}
  }
  const addRow = () => patch({rows: [...block.rows, block.rows[0].map(() => '')]});
  const addColumn = () => patch({rows: block.rows.map(row => [...row, ''])});
  const removeRow = index => patch({rows: block.rows.filter((_, i) => i !== index)});
  const removeColumn = index => patch({rows: block.rows.map(row => row.filter((_, i) => i !== index))});
  return <form className="requirements-edit-form document-controls" onSubmit={event => {event.preventDefault(); commit(block);}}>
    {block.kind === 'text' && <>
      <label>Style<select value={block.style} onChange={event => patch({style: event.target.value})}><option value="paragraph">Paragraph</option><option value="heading">Heading</option></select></label>
      <textarea autoFocus rows={4} maxLength={20000} aria-label="Document text" value={block.text} onChange={event => patch({text: event.target.value})}/>
    </>}
    {block.kind === 'image' && <>
      <label>Image file<input type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={event => void loadImage(event.target.files[0])}/></label>
      {supportedImage(block.image) && <img className="requirements-image-preview" src={block.image} alt="Selected image preview"/>}
      <label>Caption and image description<input value={block.alt} maxLength={1000} onChange={event => patch({alt: event.target.value})}/></label>
    </>}
    {block.kind === 'table' && <><div className="requirements-table-scroll"><table><tbody>
      {block.rows.map((row, index) => <tr key={index}>{row.map((cell, column) => <td key={column}>
        <input aria-label={index === 0 ? `Column ${column + 1} heading` : `Row ${index}, column ${column + 1}`} maxLength={4000} value={cell}
          onChange={event => patch({rows: block.rows.map((current, i) => i === index ? current.map((item, j) => j === column ? event.target.value : item) : current)})}/>
        {index === 0 && block.rows[0].length > 1 && <button type="button" className="link" aria-label={`Remove column ${column + 1}`} onClick={() => removeColumn(column)}>Remove</button>}
      </td>)}<td>{index > 0 && block.rows.length > 2 && <button type="button" className="link" aria-label={`Remove row ${index}`} onClick={() => removeRow(index)}>Remove</button>}</td></tr>)}
    </tbody></table></div>
      <div className="requirements-tools"><button type="button" className="btn" disabled={block.rows.length >= 100} onClick={addRow}>Add row</button>
        <button type="button" className="btn" disabled={block.rows[0].length >= 20} onClick={addColumn}>Add column</button></div>
    </>}
    <div className="requirements-tools">
      <button type="submit" className="btn primary" disabled={reading || !validDocumentBlock(block, block.id)}>Save {block.kind}</button>
      <button type="button" className="link" onClick={close}>Cancel</button>
      {original && <button type="button" className="link" onClick={() => commit(null)}>Remove {block.kind}</button>}
    </div>
    {error && <p role="alert">{error}</p>}
  </form>;
}

function PageContent({page, state, change}) {
  const [editing, setEditing] = useState(null);
  const add = kind => {
    const values = {text: {text: '', style: 'paragraph'}, table: {rows: [['', ''], ['', '']]}, image: {image: '', alt: ''}};
    setEditing({original: null, initial: {page, kind, id: crypto.randomUUID(), ...values[kind]}});
  };
  return <>
    {state.blocks.filter(block => block.page === page).map(block => <div key={block.id} className="requirements-block">
      <BlockContent block={block} linkable/>
      <div className="requirements-tools document-controls">
        <button type="button" className="link" disabled={state.changes.some(row => row.target.kind === 'block' && row.target.id === block.id)}
          onClick={() => setEditing({original: block, initial: block})}>Edit {block.kind}</button>
        <DocumentThreads threads={state.threads} anchor={`block:${block.id}`} change={change}/>
      </div>
    </div>)}
    {editing && <BlockEditor key={editing.initial.id} {...editing} change={change} close={() => setEditing(null)}/>}
    <div className="requirements-tools requirements-page-controls document-controls">
      <button type="button" className="link" onClick={() => add('text')}><FilePenLine size={15}/> Insert text</button>
      <button type="button" className="link" onClick={() => add('table')}><Table2 size={15}/> Insert table</button>
      <button type="button" className="link" onClick={() => add('image')}><ImagePlus size={15}/> Insert image</button>
      <DocumentThreads threads={state.threads} anchor={`page:${page}`} change={change}/>
    </div>
  </>;
}

function ReviewChanges({state, change, pages, nameRequirement, project}) {
  const [error, setError] = useState('');
  function decide(id, accept) {
    try {change({type: 'decide', id, accept}); setError('');} catch (failure) {setError(failure.message);}
  }
  return <section className="requirements-review document-controls" aria-label="Tracked changes">
    <h3>Tracked changes</h3>
    {!state.changes.length && <p>No pending changes.</p>}
    {state.changes.map(row => <article key={row.id}>
      <strong>{row.target.kind === 'richPage' ? pages.find(page => page.id === row.target.id)?.title || 'Document page' :
        row.target.kind === 'block' ? pages.find(page => page.id === (row.after || row.before).page)?.title || 'Document' :
        row.target.kind === 'scope' ? 'Purpose and scope' : `${nameRequirement(row.target.id)} · ${row.target.field}`}</strong>
      <div className="requirements-revision-content">
        <div><small>Previous</small>{row.target.kind === 'richPage' ? <RichPagePreview doc={row.previous}/> : row.target.kind === 'block' ? row.before ? <BlockContent block={row.before}/> : <p>New content</p> : <del>{row.before || 'Empty'}</del>}</div>
        <div><small>Proposed</small>{row.target.kind === 'richPage' ? <RichPagePreview doc={row.after.doc}/> : row.target.kind === 'block' ? row.after ? <BlockContent block={row.after}/> : <p>Remove content</p> : <ins>{row.after || 'Empty'}</ins>}</div>
      </div>
      <div className="requirements-tools">
        <button type="button" className="btn primary" onClick={() => decide(row.id, true)}>Accept change</button>
        <button type="button" className="btn" onClick={() => decide(row.id, false)}>Reject change</button>
      </div>
    </article>)}
    {error && <p role="alert">{error}</p>}
  </section>;
}

function printDocument(root, title) {
  const output = window.open('', '_blank');
  if (!output) throw Error('Allow pop-ups to print the requirements.');
  const document = output.document;
  document.title = title;
  const style = document.createElement('style');
  style.textContent = `
    @page { size: A4; margin: 17mm 17mm 19mm;
      @bottom-center { content: "Page " counter(page); font: 10pt sans-serif; color: #475569; }
    }
    body { font: 11pt/1.5 Georgia, serif; color: #172033; margin: 0; }
    .requirements-page + .requirements-page { break-before: page; }
    h1, h2, h3, h4, h5 { break-after: avoid; line-height: 1.25; }
    a { color: #172033; }
    p, td, th, figcaption { white-space: pre-wrap; overflow-wrap: anywhere; }
    figure { margin: 1em 0; break-inside: avoid; } img { max-width: 100%; max-height: 185mm; object-fit: contain; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    tr { break-inside: avoid; } th, td { border: 1px solid #94a3b8; padding: 5pt; text-align: left; }
    .document-meta { font: 9pt/1.4 sans-serif; color: #475569; }
    .requirements-contents li { margin-bottom: .35em; }
    .requirements-page-number, .requirements-contents-page { display: none; }
    @media screen { body { padding: 2rem; max-width: 780px; margin: auto; } }
  `;
  document.head.append(style);
  const copy = root.cloneNode(true);
  copy.querySelectorAll('.document-controls, .document-discuss, .design-comments, .requirement-comments, button, input, textarea, select').forEach(element => element.remove());
  document.body.append(document.importNode(copy, true));
  const images = [...document.images].map(image => image.decode().catch(() => {}));
  void Promise.all(images).then(() => {if (!output.closed) {output.focus(); output.print();}});
}

export function RequirementsDocument({project, children, cover, change, nameRequirement}) {
  const state = documentState(project);
  const paper = useRef(null);
  const contents = useRef(null);
  const editor = useRef(null);
  const opened = useRef(false);
  const dirty = useRef(false);
  const [review, setReview] = useState(false);
  const [error, setError] = useState('');
  const [workspace, setWorkspace] = useState(null);
  const [outline, setOutline] = useState(false);
  const [selectionComment, setSelectionComment] = useState(null);
  const pages = [{id: 'cover', title: project.name || 'Requirements', body: cover},
    ...React.Children.toArray(children).filter(React.isValidElement).map(section => ({
      id: section.props['data-page'], title: section.props['data-title'], body: section.props.children, related: section.props['data-related'],
    }))];
  const known = new Set(pages.map(page => page.id));
  for (const id of new Set([...state.blocks.map(block => block.page), ...(state.richPages || []).map(page => page.id)])) {
    if (!known.has(id)) pages.push({id, title: 'Additional document content', body: null});
  }
  const visible = pages.filter(page => !richPage(project, page.id)?.hidden);
  for (const page of visible) {
    const authored = richPage(project, page.id);
    if (authored) page.title = richHeadings(authored.doc)[0]?.text || page.title;
  }

  function openDocument() {
    try {
      const originals = visible.map(({id}) => {
        const before = richPage(project, id);
        const previous = before ? refreshRichBindings(project, before.doc) :
          snapshotPage(paper.current.querySelector(`[data-edit-page="${CSS.escape(id)}"]`));
        return {id, before, previous: cleanRichDocument(previous), bindings: richBindingBasis(project, previous)};
      });
      const sections = originals.map(record => ({type: 'requirementsPage', attrs: {pageId: record.id}, content: record.previous.content}));
      setWorkspace({originals, previous: {type: 'doc', content: sections.length ? sections : [newDocumentPage()]}});
      setReview(false);
      setError('');
    } catch (failure) {setError(failure.message);}
  }
  useEffect(() => {
    if (opened.current) return;
    opened.current = true;
  }, []);

  function showReadView(showReview = false) {
    if (dirty.current && !window.confirm('Discard unsaved document edits?')) return;
    dirty.current = false;
    editor.current = null;
    setWorkspace(null);
    setSelectionComment(null);
    setOutline(false);
    setReview(showReview);
  }

  function saveDocument(doc) {
    const seen = new Set();
    const updated = doc.content.map(section => {
      const originalId = section.attrs?.pageId;
      const id = originalId && !seen.has(originalId) ? originalId : `page-${crypto.randomUUID()}`;
      seen.add(id);
      const existing = workspace.originals.find(page => page.id === id);
      const content = cleanRichDocument({type: 'doc', content: section.content});
      return {id, content, ...(existing || {before: null, previous: {type: 'doc', content: [{type: 'paragraph'}]}, bindings: []})};
    });
    const edits = updated.filter(row => !row.before && !workspace.originals.some(original => original.id === row.id) ||
      JSON.stringify(row.previous) !== JSON.stringify(row.content));
    for (const removed of workspace.originals.filter(row => !seen.has(row.id))) {
      edits.push({...removed, content: removed.previous, hidden: true});
    }
    if (!edits.length) return;
    const next = change({type: 'editPages', entries: edits});
    dirty.current = false;
    if (state.tracking) {
      showReadView(true);
      return;
    }
    setWorkspace({
      ...workspace,
      originals: updated.map(row => ({
        id: row.id, before: richPage(next, row.id), previous: row.content, bindings: richBindingBasis(next, row.content),
      })),
    });
  }

  function jump(event, id) {
    event.preventDefault();
    const page = workspace ? editor.current?.view.dom.querySelector(`[data-page-id="${CSS.escape(id)}"]`)
      : paper.current.querySelector(`#${CSS.escape(id)}`);
    page?.focus({preventScroll: true});
    page?.scrollIntoView({block: 'start'});
  }

  function readPage({id, title, body, related}, index) {
    const authored = richPage(project, id);
    const isCover = id === 'cover';
    return <section key={id} id={`req-page-${id}`} className="requirements-paper requirements-page" tabIndex={-1}
      aria-label={isCover ? 'Cover and contents' : title}>
      <div data-edit-page={id}>
        {authored ? <RichPagePreview doc={refreshRichBindings(project, authored.doc)}/> : <>
          {!isCover && <h3>{title}</h3>}{body}
          <PageContent page={id} state={state} change={change}/>
        </>}
      </div>
      {isCover && <details className="requirements-contents-disclosure"><summary>Contents</summary><nav className="requirements-contents" aria-label="Table of contents" tabIndex={-1} ref={contents}>
        <h3>Table of contents</h3>
        <ol>{visible.filter(page => page.id !== 'cover').map(({id, title}) => {
          const authored = richPage(project, id);
          const headings = authored ? richHeadings(authored.doc).slice(1) : state.blocks
            .filter(block => block.page === id && block.style === 'heading')
            .map(block => ({id: `req-heading-${block.id}`, text: block.text}));
          return <li key={id}>
            <a href={`#req-page-${id}`} onClick={event => jump(event, `req-page-${id}`)}>
              <span>{title}</span><span className="requirements-contents-page">{visible.findIndex(page => page.id === id) + 1}</span>
            </a>
            {headings.length > 0 && <ol>{headings.map(heading => <li key={heading.id}>
              <a href={`#${heading.id}`} onClick={event => jump(event, heading.id)}>{heading.text}</a>
            </li>)}</ol>}
          </li>;
        })}</ol>
      </nav></details>}
      {authored && <>
        <DocumentThreads threads={state.threads} anchor={`page:${id}`} change={change}/>
        {related && <details className="requirements-threads document-controls"><summary>Requirement feedback</summary>{related}</details>}
        {state.blocks.filter(block => block.page === id && state.threads.some(row => row.anchor === `block:${block.id}`)).map(block =>
          <DocumentThreads key={block.id} threads={state.threads} anchor={`block:${block.id}`} change={change}/>)}
      </>}
      {state.changes.some(row => row.target.kind === 'richPage' && row.target.id === id) && <small className="document-controls">Page pending review</small>}
      <div className="requirements-page-number">Page {index + 1}</div>
    </section>;
  }

  return <>
    <div className="requirements-toolbar document-controls" role="group" aria-label="Document tools">
      <button type="button" className="btn primary" onClick={() => workspace ? showReadView() : openDocument()}>
        <FilePenLine size={16}/> {workspace ? 'Read view' : 'Edit document'}
      </button>
      <button type="button" className="btn" aria-expanded={workspace ? outline : undefined} onClick={() => {
        if (workspace) setOutline(!outline);
        else {const disclosure=contents.current?.closest('details');if(disclosure)disclosure.open=true;contents.current?.focus({preventScroll: true}); contents.current?.scrollIntoView({block: 'start'});}
      }}><List size={16}/> Contents</button>
      <details className="requirements-change-tools"><summary>Change tracking</summary>
      <button type="button" className="btn" aria-pressed={state.tracking} onClick={() => change({type: 'tracking', enabled: !state.tracking})}>Track changes</button>
      <button type="button" className="btn" aria-expanded={review} onClick={() => showReadView(!review)}>Review changes ({state.changes.length})</button>
      </details>
      <button type="button" className="btn" onClick={() => {
        try {
          if (dirty.current) throw Error('Save the document before printing.');
          printDocument(paper.current, project.name || 'Requirements');
          setError('');
        } catch (failure) {setError(failure.message);}
      }}><Printer size={16}/> Print / PDF</button>
      {error && <span role="alert">{error}</span>}
    </div>
    {review && <ReviewChanges state={state} change={change} pages={pages} nameRequirement={nameRequirement}/>}
    {workspace && <>
      {outline && <nav className="requirements-word-outline" aria-label="Document outline">
        <ol>{visible.map(({id, title}) => <li key={id}><a href={`#req-page-${id}`} onClick={event => jump(event, id)}>{title}</a></li>)}</ol>
      </nav>}
      <div className="requirements-writing-surface">
        <RequirementsPageEditor draft={workspace} onSave={saveDocument}
          onDirty={value => {dirty.current = value;}} onComment={setSelectionComment} onReady={value => {editor.current = value;}}/>
        {selectionComment && <aside className="requirements-comment-dock" aria-label="Comment on selected text">
          <button type="button" className="link" onClick={() => setSelectionComment(null)}>Close comments</button>
          <DocumentThreads threads={state.threads} anchor={`page:${selectionComment.page || 'cover'}`} change={change} quote={selectionComment.quote}/>
        </aside>}
      </div>
    </>}
    <div hidden={!!workspace}><article ref={paper} aria-label="Requirements document" className="requirements-pages">
      {visible.map(readPage)}
    </article></div>
  </>;
}
