// Give the browser exporter and Node compiler the same first-party assets.
// Fonts live in one shared stylesheet so file:// readers need no font server.
import fs from 'node:fs';

const read=(path,encoding)=>fs.readFileSync(new URL('../'+path,import.meta.url),encoding);
const fonts=[
  {family:'DM Sans',weight:'100 1000',file:'dm-sans-latin-wght-normal.woff2',license:'DM-Sans-OFL.txt'},
  {family:'Manrope',weight:'200 800',file:'manrope-latin-wght-normal.woff2',license:'Manrope-OFL.txt'},
];
const faces=fonts.map(font=>
  '@font-face { font-family: "'+font.family+'"; font-style: normal; font-weight: '+font.weight+
  '; font-display: swap; src: url("data:font/woff2;base64,'+read('public/fonts/'+font.file,'base64')+'") format("woff2"); }'
);
const brand={
  foundation:[...faces,read('src/atmem-tokens.css','utf8'),read('src/brand.css','utf8')].join('\n'),
  files:{
    'assets/atmem-on-light.svg':read('public/brand/atmem-horizontal-on-light.svg','utf8'),
    'assets/atmem-on-dark.svg':read('public/brand/atmem-horizontal-on-dark.svg','utf8'),
    'assets/favicon.svg':read('public/favicon.svg','utf8'),
    'assets/font-licenses.txt':fonts.map(font=>font.family+'\n\n'+read('public/fonts/'+font.license,'utf8')).join('\n\n'),
  },
};
const dest=new URL('../src/runtime/handoff-brand.json',import.meta.url);
const content=JSON.stringify(brand,null,2)+'\n';
if(!fs.existsSync(dest)||fs.readFileSync(dest,'utf8')!==content)fs.writeFileSync(dest,content);
