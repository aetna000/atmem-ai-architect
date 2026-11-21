import {describeTerraformBlockers} from '../src/terraform-emulation-blockers.mjs';
// Server-owned generator: accepts a project, never caller-supplied executable Terraform.
import { terraformSketch } from '../src/terraform.mjs';
import { validateImport } from '../src/core.mjs';
import { toProjectFile } from '../src/project-file.mjs';
let input='';for await(const chunk of process.stdin)input+=chunk;
const {project,environment}=JSON.parse(input);
const checked=validateImport(project);toProjectFile(checked);
const files=terraformSketch(checked,environment);
files['emulation-blockers.json']=JSON.stringify({version:1,blockers:describeTerraformBlockers(files,checked)},null,2)+'\n';
process.stdout.write(JSON.stringify(files));
