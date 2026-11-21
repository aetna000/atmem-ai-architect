// Assign document identity once before a draft enters autosave or engineering.
// This timestamp describes the project container, never a business/source date.
export function initializeProjectIdentity(project,{now=new Date(),newId=()=>crypto.randomUUID()}={}){
 if(project.id&&project.createdAt)return project;
 return {...project,id:project.id||newId(),createdAt:project.createdAt||now.toISOString()};
}
