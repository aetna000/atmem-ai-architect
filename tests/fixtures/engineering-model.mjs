// Synthetic library fixture for model/view mechanics, not generated client design.
export function libraryEngineeringModel(){
 const attr=(id,name,typeRef)=>({id,name,typeRef,visibility:'private'}),column=(id,name,typeRef,nullable=false)=>({id,name,typeRef,nullable});
 const operation=(id,name,input,output)=>({id,name,visibility:'public',parameters:[{id:id+'-in',name:'item',typeRef:input,direction:'in'},{id:id+'-return',name:'result',typeRef:output,direction:'return'}],preconditions:['The request identifies an existing item.'],postconditions:['The operation reports its durable outcome.']});
 const e=(id,name,kind,extra={})=>({id,name,kind,basis:'proposed',...extra});
 return{format:'atmem.engineering-model',version:1,id:'library-model',name:'Library engineering model',elements:[
  e('identity','Identifier','dataType'),e('instant','Instant','dataType'),e('text','Text','dataType'),e('state','LoanState','enumeration',{literals:['active','returned']}),
  e('loan','Loan','class',{blockId:'loans',description:'Records the lifecycle of a borrowing agreement.',attributes:[attr('loan-id','id','identity'),attr('loan-state','state','state'),attr('loan-time','borrowedAt','instant')],operations:[operation('loan-return','returnItem','identity','loan')],invariants:['A returned agreement cannot be returned again.']}),
  e('service','LoanService','class',{blockId:'loans',description:'Coordinates borrowing operations through an owned repository contract.',operations:[operation('service-accept','accept','loan','identity'),operation('service-return','returnItem','identity','loan')]}),
  e('repository','LoanRepository','interface',{blockId:'loans',operations:[operation('repo-save','save','loan','identity'),operation('repo-read','find','identity','loan')]}),
  e('store','LoanStore','class',{blockId:'loans',description:'Implements the logical repository contract with an explicit storage mapping.',operations:[operation('store-save','save','loan','identity')]}),
  e('books','BookRecord','entity',{blockId:'catalog',columns:[column('books-id','id','identity'),column('books-title','title','text')],primaryKey:['books-id']}),
  e('borrowers','BorrowerRecord','entity',{blockId:'loans',columns:[column('borrowers-id','id','identity'),column('borrowers-name','displayName','text')],primaryKey:['borrowers-id']}),
  e('records','LoanRecord','entity',{blockId:'loans',description:'Logical persistence of a borrowing agreement and its identity references.',columns:[column('records-id','id','identity'),column('records-book','bookId','identity'),column('records-borrower','borrowerId','identity'),column('records-start','borrowedAt','instant'),column('records-end','returnedAt','instant',true)],primaryKey:['records-id'],indexes:[{id:'borrower-index',name:'Borrower loans',columns:['records-borrower','records-start'],unique:false,purpose:'Find borrowing history in start-time order.'}],checks:[{id:'return-order',name:'Return time order',expression:'returnedAt is absent or not earlier than borrowedAt',language:'natural-language'}]})
 ],relationships:[
  {id:'service-repository',name:'Repository contract',kind:'dependency',source:'service',target:'repository'},
  {id:'store-repository',name:'Implements',kind:'realization',source:'store',target:'repository'},
  {id:'service-loan',name:'Coordinates',kind:'association',source:'service',target:'loan',targetEnd:{role:'agreement',multiplicity:{lower:0,upper:'*'},navigable:true}},
  {id:'loan-storage',name:'Persists as',kind:'mapping',source:'loan',target:'records'},
  {id:'loan-book',name:'Book identity',kind:'foreignKey',source:'records',target:'books',sourceColumns:['records-book'],targetColumns:['books-id'],onDelete:'restrict'},
  {id:'loan-borrower',name:'Borrower identity',kind:'foreignKey',source:'records',target:'borrowers',sourceColumns:['records-borrower'],targetColumns:['borrowers-id'],onDelete:'restrict'}
 ],diagrams:[
  {id:'classes',name:'Borrowing classes and contracts',kind:'class',placements:[{elementId:'loan',x:40,y:160},{elementId:'service',x:500,y:70},{elementId:'repository',x:980,y:70},{elementId:'store',x:980,y:430}],relationships:['service-repository','store-repository','service-loan']},
  {id:'schema',name:'Logical borrowing schema',kind:'schema',placements:[{elementId:'books',x:40,y:100},{elementId:'records',x:520,y:180},{elementId:'borrowers',x:1000,y:100}],relationships:['loan-book','loan-borrower']},
  {id:'loan-focus',name:'Agreement detail',kind:'class',placements:[{elementId:'loan',x:40,y:60}],relationships:[]}
 ]};
}
