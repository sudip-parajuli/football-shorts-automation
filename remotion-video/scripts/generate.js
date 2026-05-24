const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const LOG_FILE = path.join(__dirname, 'pipeline.log');

function log(message) {
  const timestamp = new Date().toISOString();
  const entry = `[${timestamp}] ${message}\n`;
  console.log(message);
  fs.appendFileSync(LOG_FILE, entry);
}

function getAudioDuration(filePath) {
  try {
    const result = spawnSync('ffprobe', [
      '-v', 'error',
      '-show_entries', 'format=duration',
      '-of', 'default=noprint_wrappers=1:nokey=1',
      filePath
    ]);
    if (result.status === 0) {
      return parseFloat(result.stdout.toString().trim());
    }
    throw new Error(`ffprobe failed for ${filePath}`);
  } catch (e) {
    log(`ERROR: Could not get duration for ${filePath}: ${e.message}`);
    return 0;
  }
}

function runStep(name, command, args, cwd = process.cwd()) {
  log(`Starting Step: ${name}...`);
  const safeArgs = args.map(arg => {
    if (typeof arg === 'string' && arg.includes(' ') && !arg.startsWith('"')) {
      return `"${arg}"`;
    }
    return arg;
  });
  const result = spawnSync(command, safeArgs, { cwd, stdio: 'inherit', shell: true });
  if (result.error) {
    log(`ERROR: Step ${name} failed to start: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status === 0) {
    log(`Step ${name} COMPLETED successfully.`);
    return true;
  } else {
    log(`ERROR: Step ${name} FAILED with exit code ${result.status}.`);
    process.exit(1);
  }
}

// Main Pipeline Orchestrator
async function main() {
  log("--- NEW PIPELINE RUN ---");
  
  // Step 1: Run Python logic to generate script, images, audio, render, and clean up temp assets
  // Note: We assume the user provides --topic via command line
  const args = process.argv.slice(2);
  runStep("Python Content Generation", "python", ["footybitez/long_main.py", ...args]);

  // Step 2: YouTube Upload
  runStep("YouTube Upload", "python", ["footybitez/long_upload.py"], path.join(__dirname, '../..'));

  log("--- PIPELINE COMPLETED SUCCESSFULLY ---");
}

if (require.main === module) {
  main();
}
