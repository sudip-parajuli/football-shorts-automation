import type {CaptionWord} from './SpokenCaptions';

// Keep every word. Pages change at the first spoken word of the next page.
export function editorialPages(text:string, duration:number, timing:CaptionWord[] = []) {
  const words:CaptionWord[] = timing.length ? timing : text.trim().split(/\s+/).filter(Boolean).map((word,index,all)=>({word,start:index*duration/all.length,duration:duration/all.length}));
  const pages:CaptionWord[][]=[];
  let page:CaptionWord[]=[];
  for (const word of words) {
    if (page.length && (page.length>=14 || page.map(w=>w.word).join(' ').length+word.word.length>105)) {pages.push(page);page=[];}
    page.push(word);
    if (/[.!?;:]$/.test(word.word)) {pages.push(page);page=[];}
  }
  if(page.length) pages.push(page);
  return pages.map((items,index)=>({text:items.map(w=>w.word).join(' '),start:index===0?0:items[0].start}));
}
