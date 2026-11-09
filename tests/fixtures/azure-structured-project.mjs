export function azureStructuredProject(){
 return {version:1,revision:1,name:'Azure structured workspace',provider:'azure',requirements:'Company staff submit tickets and review a schema-checked result. No app persistence or automated action.',nodes:[
  {id:'browser',position:{x:0,y:0},data:{label:'Staff browser',kind:'resource',provider:'tools',origin:'existing',binding:'web-browser'}},
  {id:'workspace',position:{x:100,y:0},data:{label:'Structured AI workspace',kind:'resource',provider:'azure',service:'Azure App Service',implementation:'azure-structured-app',config:{region:'australiaeast',outputContract:{instruction:'Classify the supplied ticket and flag uncertainty; never take an action.',fields:[{name:'topic',type:'string',description:'Request topic',values:['billing','technical','other']},{name:'uncertain',type:'boolean',description:'Whether human resolution is required'}]}}}}
 ],edges:[{id:'browser-app',source:'browser',target:'workspace',integration:'browser-https'}]};
}
