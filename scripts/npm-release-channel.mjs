export function releaseChannel(version) {
  if (/^\d+\.\d+\.\d+$/.test(version)) return 'latest';
  if (/^\d+\.\d+\.\d+-beta\.\d+$/.test(version)) return 'beta';
  throw Error('Unsupported Architect release version: ' + version);
}
