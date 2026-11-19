import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
const root = path.resolve(import.meta.dirname, "..");
const python =
  process.platform === "win32"
    ? path.join(root, ".venv/Scripts/python.exe")
    : path.join(root, ".venv/bin/python");
if (!fs.existsSync(python)) {
  console.error(
    "Install the local sidecar first: python3 -m venv .venv && .venv/bin/python -m pip install -r server/requirements.txt",
  );
  process.exit(1);
}
// Source and packaged launches provision the same default emulation prerequisites.
const env={...process.env};
if((env.ATMEM_ARCHITECT_EMULATION_ENABLED||env.ATFORMA_EMULATION_ENABLED)!=='0'){
  const {setupRuntime,applicationHome}=await import('../cli/runtime.mjs');
  const home=applicationHome(),runtime=await setupRuntime(home);
  env.ATMEM_ARCHITECT_TERRAFORM_EMULATOR_PYTHON=env.ATMEM_ARCHITECT_TERRAFORM_EMULATOR_PYTHON||env.ATFORMA_TERRAFORM_EMULATOR_PYTHON||runtime.emulatorPython;
  env.ATMEM_ARCHITECT_TERRAFORM_BIN=runtime.terraformBinary;
  env.ATMEM_ARCHITECT_PROVIDER_CACHE=env.ATMEM_ARCHITECT_PROVIDER_CACHE||env.ATFORMA_PROVIDER_CACHE||path.join(home,'cache','terraform-providers');
}
const children = [];
let ending = false;
function stop(code = 0) {
  if (ending) return;
  ending = true;
  for (const child of children) child.kill("SIGTERM");
  process.exitCode = code;
}
for (const [binary, args] of [
  [
    python,
    [
      "-m",
      "uvicorn",
      "server.app:app",
      "--host",
      "127.0.0.1",
      "--port",
      (process.env.ATMEM_ARCHITECT_SIDECAR_PORT || process.env.ATFORMA_SIDECAR_PORT) || "8766",
      "--no-access-log",
    ],
  ],
  [process.execPath, ["node_modules/vite/bin/vite.js"]],
]) {
  const child = spawn(binary, args, {
    cwd: root,
    stdio: "inherit",
    env,
  });
  children.push(child);
  child.on("exit", (code) => stop(code || 0));
  child.on("error", (error) => {
    console.error(error.message);
    stop(1);
  });
}
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
