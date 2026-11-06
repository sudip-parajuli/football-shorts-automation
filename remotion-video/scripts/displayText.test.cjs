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
