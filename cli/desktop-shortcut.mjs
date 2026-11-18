import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';

const shellQuote = value => "'" + value.replaceAll("'", "'\\''") + "'";
const psQuote = value => "'" + value.replaceAll("'", "''") + "'";

export function createDesktopShortcut({version, home, port, platform = process.platform, desktop, npmCli, node = process.execPath}) {
  if (!/^\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$/i.test(version)) throw Error('Invalid shortcut version.');
  if (!npmCli) {
    const candidate = process.env.npm_execpath;
    if (candidate && fs.existsSync(candidate)) npmCli = candidate;
    else {
      const directories = [path.dirname(node), ...(process.env.PATH || '').split(path.delimiter)];
      const executable = directories.map(folder => path.join(folder, platform === 'win32' ? 'npm.cmd' : 'npm')).find(file => fs.existsSync(file));
      if (executable) {
        const resolved = fs.realpathSync(executable);
        npmCli = platform === 'win32' ? path.join(path.dirname(resolved), 'node_modules/npm/bin/npm-cli.js') : resolved;
      }
    }
  }
  if (!npmCli || !fs.existsSync(npmCli)) throw Error('Install npm alongside Node.js before creating a desktop shortcut.');
  if (path.basename(npmCli) === 'npx-cli.js') npmCli = path.join(path.dirname(npmCli), 'npm-cli.js');
  if (!desktop && platform === 'win32') {
    const result = spawnSync('powershell.exe', ['-NoProfile', '-Command', '[Environment]::GetFolderPath("Desktop")'], {encoding:'utf8'});
    if (result.status !== 0) throw Error('Could not find your Windows Desktop.');
    desktop = result.stdout.trim();
  }
  if (!desktop && platform === 'linux') {
    const result = spawnSync('xdg-user-dir', ['DESKTOP'], {encoding:'utf8'});
    if (result.status === 0) desktop = result.stdout.trim();
  }
  desktop ||= path.join(os.homedir(), 'Desktop');
  fs.mkdirSync(desktop, {recursive:true});
  const args = [npmCli, 'exec', '--yes', '--package', `@atmem/architect@${version}`, '--', 'atmem-architect', '--data-dir', home, '--port', String(port)];
  let target;
  if (platform === 'darwin') {
    target = path.join(desktop, 'AtMem AI Architect.command');
    fs.writeFileSync(target, '#!/bin/sh\nexport PATH=' + shellQuote(path.dirname(node)) + ':"$PATH"\nexec ' + [node, ...args].map(shellQuote).join(' ') + '\n', {mode:0o755});
  } else if (platform === 'linux') {
    target = path.join(desktop, 'AtMem AI Architect.desktop');
    const quote = value => '"' + value.replace(/[\\"`$]/g, '\\$&').replaceAll('%', '%%') + '"';
    fs.writeFileSync(target, '[Desktop Entry]\nType=Application\nName=AtMem AI Architect\nComment=Open your architecture workspace\nExec=' + [node, ...args].map(quote).join(' ') + '\nTerminal=true\nIcon=applications-development\nCategories=Development;\n', {mode:0o755});
  } else if (platform === 'win32') {
    target = path.join(desktop, 'AtMem AI Architect.lnk');
    // PowerShell invokes Node with separate arguments, preserving spaces and quotes.
    const launch = '& ' + [node, ...args].map(psQuote).join(' ');
    const encoded = Buffer.from(launch, 'utf16le').toString('base64');
    const script = '$s=(New-Object -ComObject WScript.Shell).CreateShortcut(' + psQuote(target) + ');$s.TargetPath="powershell.exe";$s.Arguments=' + psQuote('-NoProfile -EncodedCommand ' + encoded) + ';$s.Save()';
    const result = spawnSync('powershell.exe', ['-NoProfile', '-Command', script], {encoding:'utf8'});
    if (result.status !== 0) throw Error('Could not create the Windows desktop shortcut.');
  } else throw Error('Desktop shortcuts support macOS, Windows and Linux.');
  return target;
}
