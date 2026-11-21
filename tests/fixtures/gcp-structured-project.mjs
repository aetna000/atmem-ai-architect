export function gcpStructuredProject(){
 return {version:1,revision:1,name:'Google structured workspace',provider:'gcp',requirements:'Company staff submit tickets and review structured suggestions. No automated actions or saved ticket input.',nodes:[
  {id:'browser',position:{x:0,y:0},data:{label:'Staff browser',kind:'resource',provider:'tools',origin:'existing',binding:'web-browser'}},
  {id:'workspace',position:{x:100,y:0},data:{label:'Structured AI workspace',kind:'resource',provider:'gcp',service:'Google Cloud Run',implementation:'gcp-structured-app',config:{region:'australia-southeast1',outputContract:{instruction:'Classify the ticket and flag uncertainty; never act on it.',fields:[{name:'topic',type:'string',description:'Topic',values:['billing','other']},{name:'uncertain',type:'boolean',description:'Needs human review'}]}}}}
 ],edges:[{id:'browser-app',source:'browser',target:'workspace',integration:'browser-https'}]};
}
