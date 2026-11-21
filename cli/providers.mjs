import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';

const native = {
  codex: ['codex', 'login'],
  'claude-code': ['claude', 'auth', 'login'],
  copilot: ['copilot', 'login'],
  'gemini-cli': ['gemini'],
};
const apiKeys = {
  openai: 'OPENAI_API_KEY',
  anthropic: 'ANTHROPIC_API_KEY',
  'gemini-api': 'GEMINI_API_KEY',
  xai: 'XAI_API_KEY',
};
const aliases = new Map([['claude', 'claude-code'], ['gemini', 'gemini-cli'], ['grok', 'xai']]);

function installed(binary) {
  const windows = process.platform === 'win32';
  const envPath = process.env.PATH || process.env.Path || '';
  const extensions = windows ? (process.env.PATHEXT || '.COM;.EXE;.BAT;.CMD').split(';') : [''];
  for (const directory of envPath.split(path.delimiter).filter(Boolean)) {
    for (const extension of extensions) {
      const candidate = path.join(directory, binary + extension);
      try {
        if (fs.statSync(candidate).isFile()) {
          fs.accessSync(candidate, windows ? fs.constants.F_OK : fs.constants.X_OK);
          return candidate;
        }
      } catch {}
    }
  }
  return null;
}

export function providerList() {
  return [
    ...Object.entries(native).map(([name, argv]) => ({
      name, method: argv.join(' '), installed: Boolean(installed(argv[0])),
    })),
    ...Object.entries(apiKeys).map(([name, variable]) => ({
      name, method: 'API key', environmentVariable: variable, environmentConfigured: Boolean(process.env[variable]),
    })),
  ];
}

async function nativeLogin(args) {
  const [command, ...argv] = args;
  const executable = installed(command);
  if (!executable) throw Error(`Install ${command} and make it available on PATH, then try again.`);
  const shim = process.platform === 'win32' && /\\.(cmd|bat)$/i.test(executable);
  const env = {...process.env};
  for (const name of [...Object.values(apiKeys), 'ANTHROPIC_AUTH_TOKEN', 'CODEX_API_KEY', 'GOOGLE_API_KEY',
    'GITHUB_TOKEN', 'GH_TOKEN', 'COPILOT_GITHUB_TOKEN']) delete env[name];
  await new Promise((resolve, reject) => {
    // Windows npm shims require cmd.exe. Only these fixed commands and arguments use it.
    const child = spawn(shim ? process.env.ComSpec || 'cmd.exe' : executable,
      shim ? ['/d', '/s', '/c', `""${executable}" ${argv.join(' ')}"`] : argv,
      {stdio: 'inherit', env, windowsHide: true, windowsVerbatimArguments: shim});
    child.once('error', reject);
    child.once('exit', (code, signal) => {
      if (code === 0) resolve();
      else reject(Error(`${command} sign-in ended with ${signal || `exit code ${code}`}.`));
    });
  });
}

export async function login(requested, {readAnswer, instance, serverUrl}) {
  if (!requested) throw Error('Choose a provider with atmemai providers, then run atmemai login NAME.');
  const provider = aliases.get(requested.toLowerCase()) || requested.toLowerCase();
  if (Object.hasOwn(native, provider)) {
    if (provider === 'gemini-cli') console.log('Choose Sign in with Google in Gemini CLI, then exit Gemini to return.');
    await nativeLogin(native[provider]);
    return;
  }
  if (!Object.hasOwn(apiKeys, provider)) throw Error('Unknown model provider. Run atmemai providers.');
  const active = await instance();
  const variable = apiKeys[provider];
  if (active.state !== 'running') throw Error(`Start Architect first, or set ${variable} before launching it.`);
  const key = process.env[variable]?.trim() || (await readAnswer(`Enter the ${provider} API key (hidden): `, true))?.trim();
  if (!key) throw Error(`No API key entered. Use an interactive terminal or set ${variable}.`);
  const base = serverUrl(active.port);
  const localRequest = () => ({signal: AbortSignal.timeout(20000), redirect: 'error'});
  const ready = await fetch(base + '/api/cli-ready', localRequest());
  if (!ready.ok || (await ready.json()).instanceId !== active.instanceId) throw Error('Architect instance changed. Try again.');
  const session = await fetch(base + '/api/session', localRequest());
  if (!session.ok) throw Error('Could not open the local Architect session. Try again.');
  const {token} = await session.json();
  if (!token) throw Error('The local Architect session is unavailable.');
  const response = await fetch(base + '/api/credentials', {
    ...localRequest(), method: 'POST', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token}`},
    body: JSON.stringify({provider, key}),
  });
  if (!response.ok) throw Error('Could not set the key. Check its format and try again.');
  console.log(`${provider} API key is configured for the running Architect session. Select the provider in AI providers.`);
}
