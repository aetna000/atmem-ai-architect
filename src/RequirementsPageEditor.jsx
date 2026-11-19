import React, {useEffect, useMemo, useRef, useState} from 'react';
import {EditorContent, useEditor, useEditorState} from '@tiptap/react';
import {generateHTML, generateJSON} from '@tiptap/core';
import {AlignCenter, AlignJustify, AlignLeft, AlignRight, Bold, ImagePlus, Italic, Link2, List, ListOrdered, MessageSquare, Redo2, Strikethrough, Table2, Underline, Undo2} from 'lucide-react';
import {cleanRichDocument, documentLink, newDocumentPage, rasterData, requirementsEditorExtensions, requirementsWorkspaceExtensions} from './requirements-rich-document.mjs';

export function snapshotPage(element) {
  const clone = element.cloneNode(true);
  clone.querySelectorAll('.document-controls, .document-discuss, .design-comments, .requirement-comments, button, input, textarea, select, iframe, video, script').forEach(item => item.remove());
  return cleanRichDocument(generateJSON(clone.innerHTML, requirementsEditorExtensions));
}

export function RichPagePreview({doc}) {
  const html = useMemo(() => generateHTML(cleanRichDocument(doc), requirementsEditorExtensions), [doc]);
  return <div className="requirements-rich-content" dangerouslySetInnerHTML={{__html: html}}/>;
}

function Tool({label, icon: Icon, active, disabled, run}) {
  return <button type="button" className="requirements-tool" aria-label={label} title={label} aria-pressed={active}
    onMouseDown={event => event.preventDefault()} disabled={disabled} onClick={run}><Icon size={16}/></button>;
}

const fonts = ['Georgia', 'Arial', 'Verdana', 'Times New Roman', 'Courier New'];
const sizes = [10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 40];
const alignments = [['left', AlignLeft], ['center', AlignCenter], ['right', AlignRight], ['justify', AlignJustify]];

function CommandMenu({label, Icon, commands}) {
  return <details className="requirements-command-menu">
    <summary title={label}><Icon size={16}/> {label}</summary>
    <div>{commands.map(([text, run, disabled]) => <button key={text} type="button" disabled={disabled}
      onMouseDown={event => event.preventDefault()} onClick={event => {
        event.currentTarget.closest('details').open = false;
        run();
      }}>{text}</button>)}</div>
  </details>;
}

function Ribbon({editor, prompt, comment}) {
  const format = useEditorState({editor, selector: ({editor: current}) => {
    const style = current.getAttributes('textStyle');
    return {
      bold: current.isActive('bold'), italic: current.isActive('italic'), underline: current.isActive('underline'),
      strike: current.isActive('strike'), bullets: current.isActive('bulletList'), numbering: current.isActive('orderedList'),
      heading: current.getAttributes('heading').level || 0,
      alignment: alignments.find(([name]) => current.isActive({textAlign: name}))?.[0] || 'left',
      font: style.fontFamily || '', size: style.fontSize || '', color: style.color || '#172033',
      table: current.isActive('table'), link: current.isActive('link'), undo: current.can().undo(), redo: current.can().redo(),
      selected: !current.state.selection.empty,
    };
  }});
  const run = action => () => action(editor.chain().focus()).run();
  const table = (label, action) => [label, run(action), !format.table];
  return <div className="requirements-edit-ribbon" role="toolbar" aria-label="Page formatting">
    <div className="requirements-ribbon-group">
      <Tool label="Undo" icon={Undo2} disabled={!format.undo} run={run(chain => chain.undo())}/>
      <Tool label="Redo" icon={Redo2} disabled={!format.redo} run={run(chain => chain.redo())}/>
    </div>
    <div className="requirements-ribbon-group">
      <select aria-label="Paragraph style" value={format.heading} onChange={event => {
        const level = Number(event.target.value);
        const active = format.heading ? 'heading' : 'paragraph';
        const requirementBinding = editor.getAttributes(active).requirementBinding || null;
        run(chain => level ? chain.setHeading({level, requirementBinding}) : chain.setNode('paragraph', {requirementBinding}))();
      }}>
        <option value={0}>Paragraph</option>
        {[1,2,3,4,5,6].map(level => <option key={level} value={level}>{level === 1 ? 'Title' : `Heading ${level - 1}`}</option>)}
      </select>
      <select aria-label="Font" value={fonts.includes(format.font) ? format.font : ''} onChange={event => {
        const font = event.target.value;
        run(chain => font ? chain.setFontFamily(font) : chain.unsetFontFamily())();
      }}>
        <option value="">Font</option>{fonts.map(font => <option key={font}>{font}</option>)}
      </select>
      <select aria-label="Font size" value={sizes.some(size => format.size === `${size}pt`) ? format.size : ''} onChange={event => {
        const size = event.target.value;
        run(chain => size ? chain.setFontSize(size) : chain.unsetFontSize())();
      }}>
        <option value="">Size</option>{sizes.map(size => <option key={size} value={`${size}pt`}>{size}</option>)}
      </select>
    </div>
    <div className="requirements-ribbon-group">
      <Tool label="Bold" icon={Bold} active={format.bold} run={run(chain => chain.toggleBold())}/>
      <Tool label="Italic" icon={Italic} active={format.italic} run={run(chain => chain.toggleItalic())}/>
      <Tool label="Underline" icon={Underline} active={format.underline} run={run(chain => chain.toggleUnderline())}/>
      <Tool label="Strikethrough" icon={Strikethrough} active={format.strike} run={run(chain => chain.toggleStrike())}/>
      <input className="requirements-color" aria-label="Text color" title="Text color" type="color"
        value={/^#[0-9a-f]{6}$/i.test(format.color) ? format.color : '#172033'} onChange={event => {
          const color = event.target.value;
          run(chain => chain.setColor(color))();
        }}/>
    </div>
    <div className="requirements-ribbon-group">
      {alignments.map(([name, Icon]) => <Tool key={name} label={name === 'justify' ? 'Justify' : `Align ${name}`} icon={Icon}
        active={format.alignment === name} run={run(chain => chain.setTextAlign(name))}/>)}
      <Tool label="Bulleted list" icon={List} active={format.bullets} run={run(chain => chain.toggleBulletList())}/>
      <Tool label="Numbered list" icon={ListOrdered} active={format.numbering} run={run(chain => chain.toggleOrderedList())}/>
    </div>
    <div className="requirements-ribbon-group">
      <CommandMenu label="Table" Icon={Table2} commands={[
        ['Insert table', run(chain => chain.insertTable({rows: 3, cols: 3, withHeaderRow: true}))],
        table('Add row below', chain => chain.addRowAfter()), table('Add column after', chain => chain.addColumnAfter()),
        table('Remove row', chain => chain.deleteRow()), table('Remove column', chain => chain.deleteColumn()),
        table('Merge or split cells', chain => chain.mergeOrSplit()), table('Remove table', chain => chain.deleteTable()),
      ]}/>
      <Tool label="Insert image" icon={ImagePlus} run={() => prompt('image')}/>
      <Tool label="Insert or edit link" icon={Link2} active={format.link} run={() => prompt('link')}/>
      <Tool label="Comment on selected text" icon={MessageSquare} disabled={!format.selected} run={comment}/>
    </div>
  </div>;
}

function InsertForm({mode, editor, close}) {
  const [value, setValue] = useState(mode === 'link' ? editor.getAttributes('link').href || '' : '');
  const [image, setImage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const load = async file => {
    if (!file) return;
    setLoading(true);
    try {
      const reader = new FileReader();
      const src = await new Promise((resolve, reject) => {
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      if (!rasterData(src)) throw Error('Choose a PNG, JPEG, GIF or WebP file.');
      const preview = new Image();
      preview.src = src;
      await preview.decode();
      setImage(src);
      setError('');
    } catch (error) {setError(error.message || 'Could not load the image.');}
    finally {setLoading(false);}
  };
  function submit(event) {
    event.preventDefault();
    if (mode === 'link') {
      const url = value.trim();
      if (!documentLink(url)) {setError('Use an HTTPS, HTTP or email link.'); return;}
      const chain = editor.chain().focus().extendMarkRange('link');
      if (editor.state.selection.empty && !editor.isActive('link')) {
        chain.insertContent({type: 'text', text: url, marks: [{type: 'link', attrs: {href: url}}]}).run();
      } else chain.setLink({href: url}).run();
    } else {
      editor.chain().focus().setImage({src: image, alt: value.trim(), title: value.trim()}).run();
    }
    close();
  }
  return <form className="requirements-edit-form document-controls" onSubmit={submit}>
    {mode === 'image' && <label>Image file<input type="file" disabled={loading}
      accept="image/png,image/jpeg,image/gif,image/webp" onChange={event => void load(event.target.files[0])}/></label>}
    <label>{mode === 'link' ? 'Link address' : 'Image description'}
      <input autoFocus={mode === 'link'} value={value} maxLength={mode === 'link' ? 2048 : 1000} onChange={event => setValue(event.target.value)}/>
    </label>
    <div className="requirements-tools">
      <button type="submit" className="btn primary" disabled={loading || !value.trim() || (mode === 'image' && !image)}>
        {mode === 'link' ? 'Apply link' : 'Insert image'}
      </button>
      {mode === 'link' && editor.isActive('link') && <button type="button" className="btn" onClick={() => {
        editor.chain().focus().extendMarkRange('link').unsetLink().run(); close();
      }}>Remove link</button>}
      <button type="button" className="link" onClick={close}>Cancel</button>
    </div>
    {error && <p role="alert">{error}</p>}
  </form>;
}

export function RequirementsPageEditor({draft, onSave, onDirty, onComment, onReady}) {
  const [insert, setInsert] = useState(null);
  const [error, setError] = useState('');
  const [dirty, setDirty] = useState(false);
  const saveRef = useRef(null);
  const editor = useEditor({
    content: draft.previous,
    extensions: requirementsWorkspaceExtensions,
    editorProps: {
      attributes: {class: 'requirements-rich-content requirements-word-content', role: 'textbox', 'aria-label': 'Document content', 'aria-multiline': 'true'},
      handleKeyDown: (_, event) => {
        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
          event.preventDefault();
          saveRef.current?.();
          return true;
        }
        return false;
      },
    },
    onUpdate: () => {setDirty(true); onDirty(true);},
  });
  useEffect(() => {if (editor) onReady(editor);}, [editor, onReady]);
  useEffect(() => {
    if (!dirty) return;
    const warn = event => {event.preventDefault(); event.returnValue = '';};
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  if (!editor) return null;
  const save = () => {
    try {
      if (dirty) {
        const uniqueIds = new Set();
        const transaction = editor.state.tr;
        editor.state.doc.forEach((node, offset) => {
          let id = node.attrs.pageId;
          if (typeof id !== 'string' || !/^[a-z0-9-]{1,100}$/i.test(id) || uniqueIds.has(id)) {
            id = `page-${crypto.randomUUID()}`;
            transaction.setNodeMarkup(offset, undefined, {...node.attrs, pageId: id});
          }
          uniqueIds.add(id);
        });
        if (transaction.docChanged) editor.view.dispatch(transaction.setMeta('addToHistory', false));
        onSave(editor.getJSON());
        setDirty(false);
        onDirty(false);
        setError('');
      }
    } catch (error) {setError(error.message);}
  };
  saveRef.current = save;
  const comment = () => {
    const {from, to} = editor.state.selection;
    const quote = editor.state.doc.textBetween(from, to, '\n').trim();
    const position = editor.state.doc.resolve(from);
    const page = position.depth >= 1 ? position.node(1).attrs.pageId : null;
    if (quote) onComment({quote, page});
  };
  return <>
    <div className="requirements-editor-toolbar document-controls" data-unsaved-requirements={dirty || undefined}>
      <Ribbon editor={editor} prompt={setInsert} comment={comment}/>
      <div className="requirements-tools requirements-editor-actions">
        <button type="button" className="btn primary" onClick={save} disabled={!dirty}>Save document</button>
        <button type="button" className="btn" onClick={() => {
          const end = editor.state.doc.content.size;
          editor.chain().insertContentAt(end, newDocumentPage()).focus().scrollIntoView().run();
        }}>New page</button>
        {dirty && <small>Unsaved edits</small>}
        {error && <span role="alert">{error}</span>}
      </div>
    </div>
    {insert && <InsertForm key={insert} mode={insert} editor={editor} close={() => setInsert(null)}/>}
    <EditorContent editor={editor}/>
  </>;
}
