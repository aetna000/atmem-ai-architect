import assert from 'node:assert/strict';import{createHash}from'node:crypto';import{strFromU8}from'fflate';
// Independent receiving ZIP checks; this never calls the producer merge function.
export function verifyReceivingCapture(files,source){
 const hash=bytes=>createHash('sha256').update(bytes).digest('hex'),receipt=JSON.parse(strFromU8(files['captured-evidence.json']));
 assert.equal(receipt.status,'verified');assert.equal(receipt.artifactId,source.artifactId);assert.equal(receipt.draftSha256,source.draftSha256);assert.equal(receipt.submittedContextSha256,source.contextSha256);
 assert.equal(hash(files['evidence/original-native-capture.zip']),receipt.artifactSha256);assert.equal(hash(files['project-context.json']),receipt.initialContextSha256);
 for(const row of receipt.files){assert.ok(files[row.path],row.path);assert.equal(files[row.path].length,row.bytes,row.path);assert.equal(hash(files[row.path]),row.sha256,row.path);}
 return {status:receipt.status,artifactId:receipt.artifactId,artifactSha256:receipt.artifactSha256,initialContextSha256:receipt.initialContextSha256,addedPayloadsVerified:receipt.files.length,archiveOnly:receipt.archiveOnly.length,boundary:'Byte custody and explicit unavailable/verified status, not target execution or semantic correctness.'};
}
