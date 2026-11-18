// Trusted native handoff, derived from the same saved Architect project as the UI.
import {createHash} from 'node:crypto';
import {fromProjectFile} from '../src/project-file.mjs';
import {specKit} from '../src/spec-kit.mjs';
import {terraformSketch} from '../src/terraform.mjs';
let input='';for await(const chunk of process.stdin)input+=chunk;
const project=fromProjectFile(JSON.parse(input)).project;
const snapshotId=createHash('sha256').update(input).digest('hex');
const now=new Date();
const files=specKit(project,{snapshotId,stamp:`Saved Architect design r${project.revision} · ${snapshotId}`,environment:'staging',now});
if(process.argv.includes('--tasks-only')){
 process.stdout.write(JSON.stringify({contextSha256:snapshotId,tasks:JSON.parse(files['spec-kit/tasks.json'])}));
}else{
 for(const [path,content] of Object.entries(terraformSketch(project,'staging')))files['terraform/'+path]=content;
 process.stdout.write(JSON.stringify(files));
}
