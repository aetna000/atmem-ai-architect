// Native nesting qualification follows the current direct canvas interaction.
if(process.env.NESTING_EVIDENCE&&!process.env.DIRECT_EVIDENCE)process.env.DIRECT_EVIDENCE=process.env.NESTING_EVIDENCE;
await import('./direct-nesting-check.mjs');
