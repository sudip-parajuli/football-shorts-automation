const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const filename = path.join(__dirname, '../src/displayText.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const captionModule = new Module(filename, module);
captionModule._compile(compiled, filename);
const { cleanDisplayFields, stripCaptionMarkup } = captionModule.exports;
const layoutFilename = path.join(__dirname, '../src/shortLayout.ts');
const layoutModule = new Module(layoutFilename, module);
layoutModule._compile(ts.transpileModule(fs.readFileSync(layoutFilename,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,layoutFilename);
test('long hooks fit both safe width and height without losing words', () => {
  for (const title of ['Who truly holds the power behind modern football transfers?', 'Why goalkeepers cannot pick up deliberate backpasses', 'X'.repeat(70)]) {
    const layout=layoutModule.exports.fitHeadline(title,820,350,(text,size)=>text.length*size*.64,98);
    assert.ok(layout.lines.every(line=>line.length*layout.fontSize*.64<=820));
    assert.ok(layout.lines.length*layout.fontSize*1.12<=350);
    assert.equal(layout.lines.join('').replace(/\s/g,''),title.toUpperCase().replace(/\s/g,''));
  }
});

test('single, double, escaped and unmatched markers never reach captions', () => {
  for (const text of ['*Messi*', '**Messi**', '\\*Messi\\*', '***Messi', 'Messi**']) {
    assert.equal(stripCaptionMarkup(text), 'Messi');
  }
});

test('all nested documentary display fields are cleaned without mutating sources or asset URLs', () => {
  const input = { chapters: [{ chapter_title: '**A career**', visual_scenes: [{
    caption: '**The goal**', typewriter_words: [{ word: '*Messi*', weight: 'xl_accent' }],
    asset_path: 'assets/photo*original.jpg',
  }] }], quiz: { question: '*Who?*', options: ['**Messi**', '*Ronaldo*'] } };
  const output = cleanDisplayFields(input);
  assert.equal(output.chapters[0].chapter_title, 'A career');
  assert.equal(output.chapters[0].visual_scenes[0].caption, 'The goal');
  assert.equal(output.chapters[0].visual_scenes[0].typewriter_words[0].word, 'Messi');
  assert.equal(output.chapters[0].visual_scenes[0].typewriter_words[0].weight, 'xl_accent');
  assert.equal(output.chapters[0].visual_scenes[0].asset_path, 'assets/photo*original.jpg');
  assert.deepEqual(output.quiz.options, ['Messi', 'Ronaldo']);
  assert.equal(input.chapters[0].chapter_title, '**A career**');
});
const pagesFilename=path.join(__dirname,'../src/editorialPages.ts');
const pagesModule=new Module(pagesFilename,module);
pagesModule._compile(ts.transpileModule(fs.readFileSync(pagesFilename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,pagesFilename);
test('editorial pages keep every word after the old eighteen-word cutoff and follow narration',()=>{
  const text='The player reviewed the contract carefully before explaining why the final decision would depend on his family and the next stage of his career rather than the size of the offer.';
  const timing=text.split(' ').map((word,index)=>({word,start:index*.7,duration:.7}));
  const pages=pagesModule.exports.editorialPages(text,25,timing);
  assert.equal(pages.map(page=>page.text).join(' '),text);
  assert.equal(pages[1].start,timing[14].start);
  for(const page of pages){
    for(const [width,height] of [[830,410],[1040,330]]){
      const fitted=layoutModule.exports.fitHeadline(page.text,width,height,(value,size)=>value.length*size*.65,88);
      assert.ok(fitted.lines.every(line=>line.length*fitted.fontSize*.65<=width));
      assert.ok(fitted.lines.length*fitted.fontSize*1.12<=height);
    }
  }
});
test('editorial fallback pages preserve all sentences without word marks',()=>{
  const text='The first sentence is complete. The second sentence remains visible until the next narrated point.';
  const pages=pagesModule.exports.editorialPages(text,12);
  assert.equal(pages.map(page=>page.text).join(' '),text);
  assert.ok(pages[1].start>0);
});
