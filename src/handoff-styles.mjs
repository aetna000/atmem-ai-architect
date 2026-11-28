// Layout for the portable reader. Colors and typography come from Architect's shared AtMem tokens.
export const handoffStyles = `
* { box-sizing: border-box; }
@media screen and (prefers-color-scheme: dark) {
  :root { color-scheme: dark; }
}
body {
  margin: 0;
  background: var(--color-bg);
  color: var(--color-ink);
  font: 400 16px/1.55 var(--type-family-sans);
}
a { color: var(--color-brand-text); text-underline-offset: .2em; }
a:hover { text-decoration: underline; }
:where(a,summary,input,[tabindex="0"]):focus-visible { outline: 3px solid var(--color-brand-text); outline-offset: 3px; }
.skip { position: absolute; left: 10px; top: -100px; z-index: 2; padding: 10px; background: var(--color-card); }
.skip:focus { top: 8px; }

.shell { display: grid; grid-template-columns: 236px minmax(0,1fr); min-height: 100vh; }
.rail {
  position: sticky; top: 0; align-self: start; height: 100vh; overflow: auto;
  padding: 25px 16px; border-right: 1px solid var(--color-line); background: var(--color-card);
}
.brand { display: inline-flex; flex-direction: column; align-items: flex-start; gap: 4px; margin-left: 10px; text-decoration: none; }
.brand picture, .brand img { display: block; width: 160px; max-width: 100%; height: auto; }
.brand-site { font: 700 13px/1.4 var(--type-family-sans); }
.brand-site span { margin-left: 2px; }
.brand:hover { text-decoration: none; }
.brand:hover .brand-site { text-decoration: underline; }
.rail-title, .eyebrow, .mast, .focus figcaption {
  font: 800 11px/1.4 var(--type-family-sans); letter-spacing: .09em; text-transform: uppercase;
}
.rail-title { margin: 39px 13px 13px; color: var(--color-muted); }
nav { display: grid; gap: 4px; }
nav a {
  display: flex; align-items: center; gap: 12px; padding: 11px 13px;
  border-radius: var(--radius-sm); text-decoration: none; color: var(--color-ink); font-size: 14px;
}
nav a:hover { background: var(--color-card-raised); color: var(--color-brand-text); text-decoration: none; }
.icon { width: 19px; height: 19px; flex: none; }

main { min-width: 0; width: 100%; max-width: 1420px; margin: 0 auto; padding: 0 clamp(20px,4.5vw,80px) 28px; }
.mast {
  min-height: 62px; display: flex; align-items: center; justify-content: space-between; gap: 12px;
  border-bottom: 1px solid var(--color-line); color: var(--color-muted);
}
.mast > :first-child { color: var(--color-brand-text); }
.view { display: none; padding-top: clamp(26px,3.8vw,54px); outline: none; overflow-wrap: anywhere; }
.view:first-of-type, .view:target { display: block; }
body:has(.view:target) .view:not(:target) { display: none; }
.eyebrow { margin: 0 0 10px; color: var(--color-brand-text); }
h1, h2, h3, .stats strong, .focus-node strong { font-family: var(--type-family-display); }
h1 { margin: 0 0 15px; font-size: clamp(36px,4.4vw,66px); line-height: 1.08; font-weight: 800; letter-spacing: -.055em; }
h2 { margin: 32px 0 13px; font-size: clamp(24px,2.25vw,32px); line-height: 1.18; font-weight: 740; letter-spacing: -.035em; }
h3 { margin: 21px 0 8px; font-size: 18px; line-height: 1.32; font-weight: 700; }
.lead { max-width: 74ch; margin: 0 0 25px; color: var(--color-muted); font-size: clamp(16px,1.4vw,20px); white-space: pre-line; }
.muted, .empty, .case-note { color: var(--color-muted); }
.empty { padding: 16px 0; }
.inline-link, .file { display: inline-flex; align-items: center; gap: 7px; font-weight: 700; }
.stats { display: grid; grid-template-columns: repeat(auto-fit,minmax(100px,1fr)); margin: 24px 0; border-block: 1px solid var(--color-line); }
.stats a, .stats div { padding: 12px 16px 13px 0; text-decoration: none; color: inherit; }
.stats strong { display: block; font-size: 29px; line-height: 1.2; font-weight: 750; letter-spacing: -.045em; }
.stats span { font-size: 13px; color: var(--color-muted); }
.stats a:hover span { color: var(--color-brand-text); text-decoration: underline; }

.focus {
  color-scheme: dark;
  margin: 24px 0 12px; padding: 18px clamp(12px,2vw,30px) 23px; overflow: hidden;
  border: 1px solid var(--color-line-strong); border-radius: var(--radius-lg);
  color: var(--color-ink); background-color: var(--color-brand-ink);
  background-image: radial-gradient(color-mix(in srgb, var(--color-brand) 38%, transparent) .8px, transparent .9px); background-size: 16px 16px;
}
.focus figcaption { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 13px; }
.focus figcaption span { display: flex; align-items: center; gap: 8px; }
.focus figcaption small { font: 550 12px var(--type-family-sans); letter-spacing: 0; text-transform: none; color: var(--color-muted); }
.focus-grid { min-height: 165px; display: grid; align-items: center; justify-content: center; }
.focus-grid.both { grid-template-columns: minmax(0,1fr) minmax(25px,.32fr) minmax(0,1fr) minmax(25px,.32fr) minmax(0,1fr); }
.focus-grid.incoming, .focus-grid.outgoing { grid-template-columns: minmax(0,240px) minmax(30px,80px) minmax(0,240px); }
.focus-grid.single { grid-template-columns: minmax(0,250px); }
.peers { height: 100%; display: grid; grid-auto-rows: 1fr; align-items: center; gap: 12px; }
.peer-card, .focus-node {
  display: flex; align-items: center; gap: 9px; min-width: 0; padding: 12px 13px;
  border: 1px solid var(--color-line); border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-brand-ink) 88%, white);
}
.peer-card strong { display: block; font-size: 15px; line-height: 1.25; }
.peer-card small { display: block; margin-top: 4px; font-size: 12px; color: var(--color-muted); }
.peer-card .icon { width: 17px; color: var(--color-brand); }
.focus-node {
  flex-direction: column; justify-content: center; min-height: 90px;
  color: var(--color-brand-ink); background: var(--color-brand); border-color: var(--color-brand); line-height: 1.22; text-align: center;
}
.focus-node strong { font-size: 18px; font-weight: 780; }
.focus-node .icon { width: 23px; height: 23px; }
.join { width: 100%; height: 100%; min-height: 135px; color: var(--color-brand); }
.mobile-direction { display: none; }
.section-line { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.section-line a, .file { font-size: 14px; }
.case-note { font-size: 13px; }

.work-index { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit,minmax(min(100%,310px),1fr)); gap: 0 28px; }
.work-index li { border-top: 1px solid var(--color-line); padding: 12px 0; }
.work-index li > div { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.work-index small, .work-index p { color: var(--color-muted); }
.work-index p { margin: 5px 0; }
.record { border-top: 1px solid var(--color-line); }
.record:last-of-type { border-bottom: 1px solid var(--color-line); }
.record summary { display: flex; align-items: baseline; gap: 12px; cursor: pointer; padding: 15px 3px; list-style: none; }
.record summary::-webkit-details-marker { display: none; }
.record summary::before { content: '+'; color: var(--color-brand-text); font-size: 19px; line-height: 1; }
.record[open] > summary::before { content: '−'; }
.record summary strong { flex: 1; font-weight: 650; }
.record summary small { color: var(--color-muted); text-align: right; }
.record-body { padding: 0 10px 16px 23px; }
.fields { margin: 0; }
.fields > div { display: grid; grid-template-columns: minmax(115px,24%) minmax(0,1fr); gap: 12px; padding: 10px 0; border-top: 1px solid var(--color-line); }
.fields dt, th { font-size: 13px; color: var(--color-muted); }
.fields dd { margin: 0; white-space: pre-line; }
.record-body ul { margin: 6px 0 12px; padding-left: 21px; }
.note { margin: 15px 0; padding: 12px 17px; border-left: 3px solid var(--color-warn); background: var(--color-warn-soft); }
.note strong { display: block; }
.cards { display: grid; grid-template-columns: repeat(auto-fit,minmax(min(235px,100%),1fr)); gap: 14px; margin: 17px 0; }
.tile { padding: 18px; border: 1px solid var(--color-line); border-radius: var(--radius-md); background: var(--color-card); }
.tile h3 { margin: 0 0 6px; }
.tile p { margin: 4px 0; color: var(--color-muted); }
.links { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 14px; }
.sheet-body { padding: 0 4px 16px; }
.drawing-frame { overflow: auto; padding: 10px; border: 1px solid var(--color-line); border-radius: var(--radius-md); background: #fafbf9; }
.drawing-frame img { display: block; width: 100%; height: auto; }
.sizing { display: inline-flex; align-items: center; gap: 6px; margin: 3px 0 8px; font-size: 13px; color: var(--color-muted); }
.sizing input { accent-color: var(--color-brand-text); }
.sheet:has(.sizing input:checked) .drawing-frame img { width: auto; max-width: none; }
.source-image { display: block; max-width: 100%; max-height: 480px; object-fit: contain; }
.image-gap { display: block; }
code { font: .86em var(--type-family-mono); overflow-wrap: anywhere; }
.view > pre, .record-body pre, .table-scroll { max-width: 100%; overflow: auto; }
table { width: 100%; border-collapse: collapse; }
td, th { text-align: left; vertical-align: top; padding: 10px 8px; border-bottom: 1px solid var(--color-line); }
.credit { margin-top: 40px; padding-top: 14px; border-top: 1px solid var(--color-line); font-size: 12px; }
.credit a { color: var(--color-muted); }

@media (max-width:900px) {
  .shell { grid-template-columns: 182px minmax(0,1fr); }
  .rail { padding-inline: 9px; }
  .brand picture, .brand img { width: 143px; }
  main { padding-inline: 24px; }
  .peer-card { padding: 8px; }
  .peer-card .icon { display: none; }
}
@media (max-width:710px) {
  .shell { display: block; }
  .rail { position: static; height: auto; padding: 8px 16px 10px; border: 0; border-bottom: 1px solid var(--color-line); }
  .brand { display: flex; flex-direction: row; align-items: center; justify-content: space-between; margin: 0; }
  .brand picture, .brand img { width: 118px; }
  .rail-title { display: none; }
  nav { display: flex; gap: 3px; flex-wrap: wrap; margin-top: 6px; }
  nav a { font-size: 12px; gap: 5px; padding: 6px 8px; }
  nav .icon { width: 14px; height: 14px; }
  main { padding: 0 16px 24px; }
  .mast { min-height: 42px; font-size: 10px; }
  .view { padding-top: 24px; }
  .stats { grid-template-columns: repeat(2,minmax(0,1fr)); margin: 16px 0; }
  .stats a, .stats div { padding: 8px; }
  .stats strong { font-size: 23px; }
  .focus figcaption { align-items: flex-start; flex-wrap: wrap; gap: 5px; }
  .focus-grid.both, .focus-grid.incoming, .focus-grid.outgoing, .focus-grid.single {
    display: flex; flex-direction: column; align-items: stretch; gap: 8px;
  }
  .focus-grid .join { display: none; }
  .focus .peers { gap: 5px; grid-auto-rows: auto; }
  .peer-card { padding: 8px 12px; }
  .peer-card > div { display: flex; gap: 8px; align-items: baseline; justify-content: space-between; width: 100%; }
  .peer-card small { margin: 0; text-align: right; }
  .focus-node { flex-direction: row; min-height: 52px; }
  .focus-node .icon { width: 17px; }
  .mobile-direction { display: block; font: 650 11px var(--type-family-sans); color: var(--color-brand); }
  .fields > div { grid-template-columns: 1fr; gap: 3px; }
  .record summary { flex-wrap: wrap; gap: 8px; }
  .record summary small { font-size: 11px; }
  .section-line { align-items: flex-start; flex-direction: column; gap: 0; }
  .record-body { padding-left: 14px; }
}
@media print {
  :root { color-scheme: light; }
  .shell, main { display: block; padding: 0; }
  .rail { position: static; height: auto; border: 0; border-bottom: 1px solid var(--color-line); padding: 0 0 8px; overflow: visible; }
  .brand { display: inline-flex; flex-direction: row; align-items: center; gap: 16px; margin: 0; }
  .brand picture, .brand img { width: 125px; }
  .rail-body, .skip, .sizing { display: none; }
  .mast { min-height: 32px; }
  body .view, body:has(.view:target) .view:not(:target) { display: block !important; break-before: page; }
  body .view:first-of-type { break-before: auto; }
  .focus, .tile, .record { break-inside: avoid; }
  .focus { print-color-adjust: exact; }
  .sheet .drawing-frame img { max-width: 100%; }
}
`;
