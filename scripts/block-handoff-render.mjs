// Fixed server-owned compiler entry point. Inputs never select executable code or paths.
import {createBlockHandoff} from '../src/block-handoff.mjs';
let input='';for await(const chunk of process.stdin){input+=chunk;if(Buffer.byteLength(input)>12_100_000)throw Error('Handoff input exceeds its explicit bound');}
const {sourceContent,blockId,generatedAt}=JSON.parse(input);
process.stdout.write(JSON.stringify(createBlockHandoff(sourceContent,blockId,{generatedAt})));
