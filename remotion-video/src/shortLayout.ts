export type Measure = (text: string, fontSize: number) => number;

export function fitHeadline(text: string, width: number, height: number, measure: Measure, maximum = 96) {
  const value = text.replace(/\\?\*/g, '').toUpperCase();
  for (let size = maximum; size >= 22; size -= 2) {
    const tokens: string[] = [];
    for (const word of value.split(/\s+/)) {
      if (measure(word, size) <= width) tokens.push(word);
      else {
        let part = '';
        for (const char of word) {
          if (part && measure(part + char, size) > width) { tokens.push(part); part = ''; }
          part += char;
        }
        if (part) tokens.push(part);
      }
    }
    const lines: string[] = [];
    for (const word of tokens) {
      const last = lines.length - 1;
      if (last >= 0 && measure(`${lines[last]} ${word}`, size) <= width) lines[last] += ` ${word}`;
      else lines.push(word);
    }
    if (lines.length * size * 1.12 <= height) return { fontSize: size, lines };
  }
  throw new Error('Headline cannot fit in its safe area');
}
