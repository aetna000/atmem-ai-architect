export function blockCheckStatus(blockId, artifact, validators, checks) {
  const registered = validators.filter(row => row.blockId === blockId);
  if (!registered.length) return { state: 'unconfigured', label: 'No independent block validator' };
  const results = registered.map(validator => checks.findLast(row =>
    typeof validator.contractSha256 === 'string' && row.blockId === blockId && row.validatorId === validator.id && row.contractSha256 === validator.contractSha256
      && row.artifactId === artifact.id && row.artifactSha256 === artifact.sha256));
  if (results.some(row => row?.state === 'finished' && row.result?.status === 'failed')) {
    return { state: 'failed', label: 'Local block check failed' };
  }
  if (results.every(row => row?.state === 'finished' && row.result?.status === 'passed'
    && row.result.artifactSha256 === artifact.sha256 && row.result.testsReported > 0 && row.result.skipped === 0)) {
    return { state: 'passed', label: 'Local block checks passed' };
  }
  return { state: 'pending', label: 'Local block checks pending' };
}
