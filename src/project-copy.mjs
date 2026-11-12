// Reuse design knowledge without reusing another project's live execution identity.
export function copyProject(project,id,createdAt=new Date().toISOString()){
 if(!id||id===project.id)throw Error('A project copy needs a new identity.');
 const copy=structuredClone(project),origin={projectId:project.id,revision:project.revision,createdAt};
 copy.id=id;copy.name=`${project.name} (copy)`;copy.createdAt=createdAt;
 copy.extensions={...copy.extensions,projectOrigin:origin};
 for(const key of ['architectureWork','architectureActivity','journey'])delete copy.extensions[key];
 for(const message of copy.extensions.conversation?.messages||[]){delete message.workState;delete message.requestId;}
 return copy;
}
