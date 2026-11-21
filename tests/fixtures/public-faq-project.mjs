import {PUBLIC_FAQ_SERVICES} from '../../src/public-faq.mjs';
export function publicFaqProject(provider='aws'){
 return {version:1,revision:1,name:'Public help assistant',provider,requirements:'Anonymous visitors ask about twenty genuinely public UTF-8 help articles under 30 KB each. Cite supporting sources and abstain when unknown. A separate authorized company editor can update/remove articles. Five questions at once; prefer Australia and document processing limits. No private sources.',nodes:[
  {id:'browser',position:{x:0,y:0},data:{label:'Public visitor',kind:'resource',provider:'tools',origin:'existing',binding:'web-browser'}},
  {id:'faq',position:{x:100,y:0},data:{label:'Public help assistant',kind:'resource',provider,service:PUBLIC_FAQ_SERVICES[provider],implementation:'public-faq-app',config:{region:{aws:'ap-southeast-2',azure:'australiaeast',gcp:'australia-southeast1',ibm:'au-syd'}[provider]}}}
 ],edges:[{id:'browser-faq',source:'browser',target:'faq',integration:'browser-https'}]};
}
