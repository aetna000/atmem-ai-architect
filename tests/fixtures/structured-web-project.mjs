export function structuredWebProject(){
 const node=(id,provider,service,implementation,kind='resource')=>({id,position:{x:0,y:0},data:{label:id,kind,provider,service,implementation,config:{region:'ap-southeast-2'}}});
 const p={version:1,revision:1,name:'Structured AI workspace',provider:'aws',requirements:'Staff submit synthetic requests and review topic and uncertainty. No raw input retention.',nodes:[
  {id:'browser',position:{x:0,y:0},data:{label:'Staff browser',kind:'resource',provider:'tools',origin:'existing',binding:'web-browser'}},
  node('web','aws','Amazon CloudFront','structured-web-app'),node('identity','aws','Amazon Cognito','structured-user-pool'),node('api','aws','Amazon API Gateway','structured-api'),node('operation','aws','AWS Lambda','bedrock-structured'),
  {id:'model',position:{x:0,y:0},data:{label:'Regional model endpoint',kind:'resource',provider:'aws',service:'Amazon Bedrock',origin:'existing',binding:'aws-bedrock-model'}}
 ],edges:[{id:'browser-web',source:'browser',target:'web',integration:'browser-https'},{id:'web-api',source:'web',target:'api',integration:'web-rag-api'},{id:'web-identity',source:'web',target:'identity',integration:'oauth-pkce'},{id:'identity-api',source:'identity',target:'api',integration:'jwt-authorizer'},{id:'api-worker',source:'api',target:'operation',integration:'http-api-lambda'},{id:'worker-model',source:'operation',target:'model',integration:'bedrock-converse'}]};
 p.nodes[4].data.config={region:'ap-southeast-2',maxInputBytes:20000,outputContract:{instruction:'Classify the request; flag uncertainty.',fields:[{name:'topic',type:'string',description:'Request topic',values:['billing','technical','other']},{name:'uncertain',type:'boolean',description:'Whether human resolution is needed'}]}};
 return p;
}
