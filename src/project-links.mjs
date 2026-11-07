export function projectIdFromUrl(value){
 try{const id=new URL(value).searchParams.get('project');return id&&/^[A-Za-z0-9-]{8,64}$/.test(id)?id:null;}catch{return null;}
}
