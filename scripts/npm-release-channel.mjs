export function releaseChannel(version) {
  if (/^\d+\.\d+\.\d+$/.test(version)) return 'latest';
  if (/^\d+\.\d+\.\d+-beta\.\d+$/.test(version)) return 'beta';
  if (/^\d+\.\d+\.\d+-review\.\d+$/.test(version)) return 'review';
  throw Error('Unsupported Architect release version: ' + version);
}
