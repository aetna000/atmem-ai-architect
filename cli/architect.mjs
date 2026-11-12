#!/usr/bin/env node
import {main} from './runtime.mjs';
main().catch(error=>{console.error(`AtMem Architect: ${error.message}`);process.exitCode=1;});
