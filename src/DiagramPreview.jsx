import React, {useEffect, useId, useState} from 'react';
import {scenarioDiagrams} from './block-spec.mjs';

let renderer;
async function renderDiagram(id, source) {
  renderer ??= import('mermaid').then(({default: mermaid}) => {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      suppressErrorRendering: true,
      fontFamily: 'sans-serif',
      flowchart: {htmlLabels: false, useMaxWidth: false},
      sequence: {useMaxWidth: false, wrap: true},
    });
    return mermaid;
  });
  return (await renderer).render(id, source);
}

export default function DiagramPreview({scenario}) {
  const [view, setView] = useState('sequence');
  const [fit, setFit] = useState(true);
  const [result, setResult] = useState(null);
  const id = 'diagram' + useId().replaceAll(/[^a-zA-Z0-9]/g, '');
  const source = scenarioDiagrams(scenario)[view];
  useEffect(() => {
    let stopped = false;
    let url;
    setResult(null);
    renderDiagram(id, source).then(({svg}) => {
      if (stopped) return;
      url = URL.createObjectURL(new Blob([svg], {type: 'image/svg+xml'}));
      setResult({source, url});
    }).catch(() => {
      if (!stopped) setResult({source, error: 'This diagram could not be rendered. Its source is available below.'});
    });
    return () => {
      stopped = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [id, source]);
  const current = result?.source === source ? result : null;
  return <section className="scenario-diagram" aria-label={scenario.name + ' diagram'}>
    <label>Diagram view
      <select value={view} onChange={event => setView(event.target.value)}>
        <option value="sequence">Sequence</option>
        <option value="functional">Functional flow</option>
        <option value="events">Events and messages</option>
      </select>
    </label>
    {!current && <p role="status">Rendering diagram…</p>}
    {current?.error && <p role="alert">{current.error}</p>}
    {current?.url && <>
      <button className="btn" aria-pressed={fit} onClick={()=>setFit(value=>!value)}>{fit?'View actual size':'Fit diagram'}</button>
      <div className="scenario-diagram-scroll" data-fit={fit}><img src={current.url} alt={scenario.name + ' ' + view + ' diagram'}/></div>
      <a href={current.url} download={view + '.svg'}>Download SVG</a>
    </>}
    <details><summary>Diagram source</summary><pre>{source}</pre></details>
  </section>;
}
