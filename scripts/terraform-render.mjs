// Server-owned generator: accepts a project, never caller-supplied executable Terraform.
import { terraformSketch } from '../src/terraform.mjs';
import { validateImport } from '../src/core.mjs';
import { toProjectFile,fromProjectFile,reviewDesignSnapshot,reviewDesignContent } from '../src/project-file.mjs';
import {createHash} from 'node:crypto';
let input='';for await(const chunk of process.stdin)input+=chunk;
const {project,environment,review}=JSON.parse(input);
const checked=project?.format?fromProjectFile(project).project:validateImport(project);const design=reviewDesignSnapshot(checked);
const files=terraformSketch(checked,environment);
const designSha256=createHash('sha256').update(reviewDesignContent(checked)).digest('hex');
process.stdout.write(JSON.stringify(review?{files,design,designSha256}:files));
