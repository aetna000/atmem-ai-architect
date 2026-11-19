// Synthetic reservation model for capture and browser tests.
export function reservationSystemModel() {
  const element=(id,kind,name,description,attributes={})=>({
    id,kind,name,description,basis:'proposed',requirementIds:['unique-reservation'],...attributes,
  });
  const port=(id,kind,ownerId,direction)=>element(id,kind,id,'Transfers a reservation decision input or output.',{ownerId,direction});
  const exchange=(id,kind,name,source,target,items,extra={})=>({
    ...element(id,kind,name,'Transfer '+items.join(' and ')+' between the declared endpoints.'),
    source,target,items,...extra,
  });
  return {
    format:'atmem.system-model',version:1,id:'reservation-system',
    elements:[
      element('clerk','actor','Box office clerk','Starts a numbered-item reservation.'),
      element('ledger','component','Inventory ledger','Tracks which numbered items remain available.',{blockId:'Ledger'}),
      element('allocator','component','Reservation allocator','Owns the exclusive reservation decision.',{blockId:'Reservations',parentId:'ledger'}),
      element('receive','function','Receive reservation','Validate the requested item and submit an allocation.',{allocatedTo:'ledger'}),
      element('allocate','function','Acquire exclusive hold','Commit exactly one durable hold per available item.',{allocatedTo:'allocator'}),
      port('clerk-request','componentPort','clerk','out'),
      port('ledger-in','componentPort','ledger','in'),
      port('ledger-out','componentPort','ledger','out'),
      port('allocator-in','componentPort','allocator','in'),
      port('receive-out','functionPort','receive','out'),
      port('allocate-in','functionPort','allocate','in'),
    ],
    exchanges:[
      exchange('submit','component','Submit reservation','clerk-request','ledger-in',['Item number']),
      exchange('reserve-item','component','Reserve item','ledger-out','allocator-in',['Item ID','Request ID'],{interfaceId:'reserve'}),
      exchange('verified-request','functional','Validated reservation','receive-out','allocate-in',['Item ID','Request ID'],{componentExchangeId:'reserve-item'}),
    ],
    diagrams:[
      {id:'logical',kind:'components',name:'Reservation architecture',elementIds:['clerk','ledger','allocator'],exchangeIds:['submit','reserve-item']},
      {id:'flow',kind:'functions',name:'Exclusive hold flow',elementIds:['receive','allocate'],exchangeIds:['verified-request']},
      {id:'scenario',kind:'sequence',name:'Reserve a numbered item',elementIds:['clerk','ledger','allocator'],exchangeIds:['submit','reserve-item']},
      {id:'retry',kind:'sequence',name:'Retry after timeout',elementIds:['ledger','allocator'],exchangeIds:['reserve-item','reserve-item']},
    ],
  };
}
