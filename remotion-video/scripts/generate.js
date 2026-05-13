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
  const result = spawnSync(command, args, { cwd, stdio: 'inherit' });
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
  
  // Step 1: Run Python logic to generate script, images, and audio
  // Note: We assume the user provides --topic via command line
  const args = process.argv.slice(2);
  runStep("Python Content Generation", "python", ["footybitez/long_main.py", ...args]);

  // Step 2: Remotion Rendering
  // Note: long_main.py is expected to write public/props.json
  runStep("Remotion Render", "npx", ["remotion", "render", "src/index.ts", "MainVideo", "output/video.mp4"], path.join(__dirname, '..'));

  log("--- PIPELINE COMPLETED SUCCESSFULLY ---");
}

if (require.main === module) {
  main();
}
