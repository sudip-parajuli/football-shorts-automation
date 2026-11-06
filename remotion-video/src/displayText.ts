/** Formatting markers are metadata, never visible caption characters. */
export const stripCaptionMarkup = (text: string): string => text.replace(/\\?\*/g, '');

const DISPLAY_FIELDS = new Set([
  'text', 'word', 'caption', 'title', 'chapter_title', 'question', 'question_text',
  'emphasis_phrase', 'explanation', 'options', 'label', 'motion_label', 'name',
  'description', 'unit', 'metric', 'club', 'event', 'timeline_title',
]);

export function cleanDisplayFields<T>(value: T, field = ''): T {
  if (typeof value === 'string') {
    return (DISPLAY_FIELDS.has(field) ? stripCaptionMarkup(value) : value) as T;
  }
  if (Array.isArray(value)) {
    return value.map(item => cleanDisplayFields(item, field)) as T;
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, cleanDisplayFields(item, key)])) as T;
  }
  return value;
}
