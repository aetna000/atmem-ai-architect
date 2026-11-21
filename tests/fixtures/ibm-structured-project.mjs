export function ibmStructuredProject(){
 return {version:1,revision:1,name:'IBM structured workspace',provider:'ibm',requirements:'Ten staff sign in and submit synthetic or redacted tickets for human-reviewed suggestions. No customer actions or saved input.',nodes:[
  {id:'browser',position:{x:0,y:0},data:{label:'Staff browser',kind:'resource',provider:'tools',origin:'existing',binding:'web-browser'}},
  {id:'workspace',position:{x:100,y:0},data:{label:'Structured AI workspace',kind:'resource',provider:'ibm',service:'IBM Code Engine',implementation:'ibm-structured-app',config:{region:'au-syd',outputContract:{instruction:'Classify the ticket and flag uncertainty; never take action.',fields:[{name:'topic',type:'string',description:'Topic',values:['billing','other']},{name:'uncertain',type:'boolean',description:'Needs human review'}]}}}}
 ],edges:[{id:'browser-app',source:'browser',target:'workspace',integration:'browser-https'}]};
}
