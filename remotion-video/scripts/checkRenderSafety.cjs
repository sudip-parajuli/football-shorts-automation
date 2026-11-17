const {spawnSync}=require('node:child_process');
const path=require('node:path');
const fs=require('node:fs');
const cli=path.join(path.dirname(require.resolve('@remotion/cli/package.json')),'remotion-cli.js');
function render(id){
  return spawnSync(process.execPath,[cli,'still','scripts/fixtures/layoutSafety.tsx',id,`out/${id}.png`,'--frame=2','--log=error'],{encoding:'utf8',timeout:180000});
}
const good=render('SafeText');
if(good.status!==0) throw new Error(`Safe layout failed: ${good.stderr}\n${good.stdout}`);
// An old file must not make a rejected render look like a successful artifact.
fs.rmSync('out/UnsafeText.png',{force:true});
const bad=render('UnsafeText');
if(bad.status===0 || !`${bad.stderr}\n${bad.stdout}`.includes('Text outside its safe layout')) throw new Error(`Overflow was not rejected by the layout guard: ${bad.stderr}\n${bad.stdout}`);
console.log('Safe layout rendered; overflowing text was blocked.');
