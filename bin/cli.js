#!/usr/bin/env node

/**
 * ALD-01 — Advanced Local Desktop Intelligence
 * Global CLI wrapper for the Python-based AI agent system.
 *
 * This script ensures Python + the ald-01 pip package are available,
 * installs them if missing, and proxies every command transparently.
 *
 * Usage:
 *   npm install -g ald-01
 *   ald-01 chat
 *   ald-01 dashboard
 *   ald-01 doctor
 */

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

// ── Colour helpers (no dependencies) ────────────────────────
const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  cyan: "\x1b[36m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  red: "\x1b[31m",
  magenta: "\x1b[35m",
  white: "\x1b[37m",
  bg_cyan: "\x1b[46m",
  bg_black: "\x1b[40m",
};

function banner() {
  console.log();
  console.log(
    `${c.cyan}${c.bold}  ╔═══════════════════════════════════════════════╗${c.reset}`
  );
  console.log(
    `${c.cyan}${c.bold}  ║              A L D - 0 1                     ║${c.reset}`
  );
  console.log(
    `${c.cyan}${c.bold}  ║     Advanced Local Desktop Intelligence      ║${c.reset}`
  );
  console.log(
    `${c.cyan}${c.bold}  ╚═══════════════════════════════════════════════╝${c.reset}`
  );
  console.log();
}

// ── Python detection ────────────────────────────────────────
function findPython() {
  const candidates =
    process.platform === "win32"
      ? ["python", "python3", "py"]
      : ["python3", "python"];

  for (const cmd of candidates) {
    try {
      const version = execSync(`${cmd} --version 2>&1`, {
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      }).trim();

      const match = version.match(/Python (\d+)\.(\d+)/);
      if (match) {
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        if (major === 3 && minor >= 10) {
          return { cmd, version };
        }
      }
    } catch {
      // not found, try next
    }
  }
  return null;
}

// ── pip package check ───────────────────────────────────────
function isAldInstalled(pythonCmd) {
  try {
    execSync(`${pythonCmd} -m ald01 --help 2>&1`, {
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });
    return true;
  } catch {
    // Also check via pip list
    try {
      const list = execSync(`${pythonCmd} -m pip list 2>&1`, {
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      return list.toLowerCase().includes("ald-01");
    } catch {
      return false;
    }
  }
}

// ── Install the pip package ─────────────────────────────────
function installPipPackage(pythonCmd) {
  console.log(
    `${c.yellow}[ald-01]${c.reset} Installing Python package...`
  );
  console.log(
    `${c.dim}         Running: ${pythonCmd} -m pip install ald-01${c.reset}`
  );
  console.log();

  try {
    execSync(`${pythonCmd} -m pip install ald-01`, {
      stdio: "inherit",
    });
    console.log();
    console.log(
      `${c.green}[ald-01]${c.reset} ${c.bold}Python package installed successfully.${c.reset}`
    );
    return true;
  } catch {
    // If PyPI package not found, try installing from git
    console.log(
      `${c.yellow}[ald-01]${c.reset} PyPI package not found. Installing from GitHub...`
    );
    try {
      execSync(
        `${pythonCmd} -m pip install git+https://github.com/aditya4232/ALD-01.git`,
        { stdio: "inherit" }
      );
      console.log();
      console.log(
        `${c.green}[ald-01]${c.reset} ${c.bold}Installed from GitHub successfully.${c.reset}`
      );
      return true;
    } catch {
      return false;
    }
  }
}

// ── Main ────────────────────────────────────────────────────
function main() {
  const args = process.argv.slice(2);

  // Handle --version flag locally
  if (args.includes("--version") || args.includes("-v")) {
    const pkg = require("../package.json");
    console.log(`ald-01 v${pkg.version} (npm wrapper)`);

    const py = findPython();
    if (py) {
      try {
        const pyVer = execSync(
          `${py.cmd} -c "import ald01; print(ald01.__version__)" 2>&1`,
          { encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }
        ).trim();
        console.log(`ald-01 v${pyVer} (python core)`);
      } catch {
        console.log(`ald-01 python core: not installed`);
      }
    }
    console.log(`${py ? py.version : "Python: not found"}`);
    console.log(`Node.js ${process.version}`);
    process.exit(0);
  }

  // Handle --help with no args
  if (args.length === 0) {
    banner();
    console.log(
      `${c.white}  Your personal AI agent system — 10+ free providers,${c.reset}`
    );
    console.log(
      `${c.white}  5 specialized agents, advanced reasoning, and a${c.reset}`
    );
    console.log(
      `${c.white}  professional web dashboard.${c.reset}`
    );
    console.log();
    console.log(`${c.bold}  Quick Start:${c.reset}`);
    console.log(
      `${c.dim}  $${c.reset} ${c.cyan}ald-01 setup${c.reset}        Run the setup wizard`
    );
    console.log(
      `${c.dim}  $${c.reset} ${c.cyan}ald-01 chat${c.reset}         Start interactive chat`
    );
    console.log(
      `${c.dim}  $${c.reset} ${c.cyan}ald-01 dashboard${c.reset}    Launch web dashboard`
    );
    console.log(
      `${c.dim}  $${c.reset} ${c.cyan}ald-01 doctor${c.reset}       System health check`
    );
    console.log(
      `${c.dim}  $${c.reset} ${c.cyan}ald-01 ask "..."${c.reset}    Quick question`
    );
    console.log();
    console.log(
      `${c.dim}  Run ${c.reset}${c.cyan}ald-01 --help${c.reset}${c.dim} for all commands.${c.reset}`
    );
    console.log();
  }

  // ── Ensure Python is available ────────────────────────────
  const py = findPython();

  if (!py) {
    banner();
    console.error(
      `${c.red}${c.bold}  Error: Python 3.10+ is required but not found.${c.reset}`
    );
    console.log();
    console.log(`${c.white}  Install Python from:${c.reset}`);
    console.log(
      `${c.cyan}  https://www.python.org/downloads/${c.reset}`
    );
    console.log();
    console.log(
      `${c.dim}  After installing, run this command again.${c.reset}`
    );
    console.log();
    process.exit(1);
  }

  // ── Ensure pip package is installed ───────────────────────
  if (!isAldInstalled(py.cmd)) {
    banner();
    console.log(
      `${c.yellow}[ald-01]${c.reset} First run detected. Setting up ALD-01...`
    );
    console.log(
      `${c.dim}         Using ${py.version}${c.reset}`
    );
    console.log();

    const installed = installPipPackage(py.cmd);
    if (!installed) {
      console.error();
      console.error(
        `${c.red}[ald-01]${c.reset} ${c.bold}Failed to install the Python package.${c.reset}`
      );
      console.log();
      console.log(`${c.white}  Try installing manually:${c.reset}`);
      console.log(
        `${c.cyan}  pip install git+https://github.com/aditya4232/ALD-01.git${c.reset}`
      );
      console.log();
      process.exit(1);
    }
    console.log();
  }

  // ── Proxy to Python CLI ───────────────────────────────────
  if (args.length === 0) {
    // We already showed help above, now also show Python help
    const child = spawn(py.cmd, ["-m", "ald01", "--help"], {
      stdio: "inherit",
    });
    child.on("close", (code) => process.exit(code || 0));
    return;
  }

  const child = spawn(py.cmd, ["-m", "ald01", ...args], {
    stdio: "inherit",
    env: { ...process.env },
  });

  child.on("error", (err) => {
    console.error(
      `${c.red}[ald-01]${c.reset} Failed to start: ${err.message}`
    );
    process.exit(1);
  });

  child.on("close", (code) => {
    process.exit(code || 0);
  });
}

main();
