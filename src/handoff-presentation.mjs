// Plain HTML is shared by browser exports and the offline Node compiler.
// Only the renderer supplies markup. All project text crosses this escape boundary.
export const html = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[char]);

const glyphs = {
  overview: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  diagrams: '<rect x="3" y="9" width="6" height="6" rx="1.5"/><rect x="15" y="2" width="6" height="6" rx="1.5"/><rect x="15" y="16" width="6" height="6" rx="1.5"/><path d="M9 12h3V5h3m-3 7v7h3"/>',
  scope: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="m7 9 1 1 2-3m2 2h5M7 15h3m2 0h5"/>',
  build: '<path d="m12 2 9 5v10l-9 5-9-5V7zM3 7l9 5 9-5m-9 5v10"/>',
  operations: '<path d="M2 12h5l3-8 4 16 3-8h5"/>',
  evidence: '<path d="m12 2 8 3v6c0 5-3 8-8 11-5-3-8-6-8-11V5z"/><path d="m8 12 3 3 5-6"/>',
  peer: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/>',
  files: '<path d="M3 7V5h6l2 2h10v12H3z"/>',
};
export function icon(name) {
  return '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'+glyphs[name]+'</svg>';
}

export function list(items, empty) {
  return items.length ? '<ul>'+items.map(item=>'<li>'+html(item)+'</li>').join('')+'</ul>' : '<p class="muted">'+html(empty)+'</p>';
}
export function fields(pairs) {
  return '<dl class="fields">'+pairs.filter(([,value])=>value!=null && value!=='').map(([key,value])=>
    '<div><dt>'+html(key)+'</dt><dd>'+html(value)+'</dd></div>').join('')+'</dl>';
}
export function disclosure(name, meta, body) {
  return '<details class="record"><summary><strong>'+html(name)+'</strong><small>'+html(meta)+'</small></summary><div class="record-body">'+body+'</div></details>';
}
export function fileLink(path, title, files) {
  if(!Object.hasOwn(files,path))return '';
  const label=html(title);
  const href='./'+path.split('/').map(encodeURIComponent).join('/');
  return '<a class="file" href="'+html(href)+'">'+label+' <span aria-hidden="true">↗</span></a>';
}

export function websiteShell({title, name, revision, sections, root='.'}) {
  const first=sections[0].id;
  const select=sections.map(({id})=>'body:has(#'+id+':target) nav a[href="#'+id+'"]').join(',');
  const assets=root+'/assets/';
  const brand='<a class="brand" href="https://atmem.ai/" target="_blank" rel="noopener noreferrer">'+
    '<picture><source media="screen and (prefers-color-scheme: dark)" srcset="'+assets+'atmem-on-dark.svg">'+
    '<img src="'+assets+'atmem-on-light.svg" width="160" height="63" alt="AtMem AI Architect"></picture>'+
    '<span class="brand-site">atmem.ai <span aria-hidden="true">↗</span></span></a>';
  const nav=sections.map(({id,label,glyph})=>'<a href="#'+id+'">'+icon(glyph)+'<span>'+html(label)+'</span></a>').join('');
  const head='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<meta name="generator" content="AtMem AI Architect"><meta name="referrer" content="no-referrer">'+
    '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' data:; style-src \'self\' \'unsafe-inline\'; font-src data:; base-uri \'none\'; form-action \'none\'">'+
    '<title>'+html(name)+' · '+html(title)+' · AtMem AI Architect</title>'+
    '<link rel="icon" type="image/svg+xml" href="'+assets+'favicon.svg"><link rel="stylesheet" href="'+assets+'handoff.css">'+
    '<style>body:not(:has(.view:target)) nav a[href="#'+first+'"],'+select+
    '{background:var(--color-brand-soft);color:var(--color-brand-text);box-shadow:inset 3px 0 var(--color-brand-text);font-weight:700}</style>';
  const credit='<footer class="credit"><a href="https://x.com/lostonwww" target="_blank" rel="noopener noreferrer">Logo by @lostonwww</a></footer>';
  return '<!doctype html><html lang="en"><head>'+head+'</head><body>'+
    '<a class="skip" href="#main">Skip to content</a><div class="shell"><aside class="rail">'+brand+
    '<div class="rail-body"><p class="rail-title">Contents</p><nav aria-label="Handoff sections">'+nav+'</nav></div></aside>'+
    '<main id="main" tabindex="-1"><div class="mast"><span>'+html(title)+'</span><span>Design revision '+html(revision)+'</span></div>'+
    sections.map(({id,body})=>'<section class="view" id="'+id+'" tabindex="-1">'+body+'</section>').join('')+credit+'</main></div></body></html>';
}

// A one-hop overview has unambiguous arrows even when the full board has cycles.
// Every edge, including omitted neighbours or parallel edges, remains in the atlas.
export function focusMap(nodes, edges, focusId) {
  if(!nodes.length)return '<p class="empty">Add components to the board to see their connections here.</p>';
  const byId=new Map(nodes.map(node=>[node.id,node]));
  const incident=new Map(nodes.map(node=>[node.id,0]));
  for(const edge of edges){
    if(incident.has(edge.source))incident.set(edge.source,incident.get(edge.source)+1);
    if(incident.has(edge.target))incident.set(edge.target,incident.get(edge.target)+1);
  }
  const focus=byId.get(focusId)||nodes.reduce((a,b)=>incident.get(b.id)>incident.get(a.id)?b:a);
  const incoming=edges.filter(edge=>edge.target===focus.id), outgoing=edges.filter(edge=>edge.source===focus.id);
  function peers(records,side){
    if(!records.length)return '';
    const shown=records.slice(0,3);
    const cards=shown.map(edge=>{
      const other=byId.get(side==='in'?edge.source:edge.target);
      const glyph={guard:'evidence',output:'files',tool:'build'}[other?.data.kind]||'peer';
      return '<div class="peer-card">'+icon(glyph)+'<div><strong>'+html(other?.data.label|| (side==='in'?edge.source:edge.target))+'</strong><small>'+html(edge.label||'Connection')+'</small></div></div>';
    }).join('');
    const ports=shown.map((_,i)=>(i+.5)*100/shown.length);
    const paths=ports.map(y=>'M0 '+y+'H25C53 '+y+' 39 50 65 50H100').join(' ');
    const heads=(side==='in'?[50]:ports).map(y=>'M93 '+(y-3)+' 100 '+y+' 93 '+(y+3)).join(' ');
    const join='<svg class="join" aria-hidden="true" viewBox="0 0 100 100" preserveAspectRatio="none"><g fill="none" stroke="currentColor"><path d="'+paths+'" '+(side==='out'?'transform="translate(100 0) scale(-1 1)"':'')+' vector-effect="non-scaling-stroke"/><path d="'+heads+'" vector-effect="non-scaling-stroke"/></g></svg>';
    const stack='<div class="peers"><b class="mobile-direction">'+(side==='in'?'Incoming':'Outgoing')+'</b>'+cards+'</div>';
    return side==='in'?stack+join:join+stack;
  }
  const count=incoming.length+outgoing.length, shown=Math.min(3,incoming.length)+Math.min(3,outgoing.length);
  const layout=incoming.length&&outgoing.length?'both':incoming.length?'incoming':outgoing.length?'outgoing':'single';
  return '<figure class="focus"><figcaption><span>'+icon('diagrams')+' Component connections</span><small>'+shown+' of '+count+' shown</small></figcaption><div class="focus-grid '+layout+'">'+
    peers(incoming,'in')+'<div class="focus-node">'+icon('build')+'<strong>'+html(focus.data.label)+'</strong></div>'+peers(outgoing,'out')+'</div></figure>';
}
