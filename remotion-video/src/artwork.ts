import type {CaptionWord} from './SpokenCaptions';
export interface ArtLayer {svg:string;anchor:string;motion:'draw'|'float'|'pulse'}
export interface Artwork extends ArtLayer {layers?:ArtLayer[]}
const normalize=(value:string)=>value.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu,'').trim();

// The object enters when its narrated anchor is spoken, then holds its place.
export function layerStartFrames(layers:ArtLayer[],timing:CaptionWord[],fps:number,duration:number):number[] {
  const words=timing.map(word=>normalize(word.word));
  return layers.map((layer,index)=>{
    if(index===0) return 0;
    const phrase=normalize(layer.anchor).split(/\s+/);
    const anchor=words.findIndex((_,start)=>phrase.every((word,offset)=>words[start+offset]===word));
    const start=anchor>=0?Math.round(timing[anchor].start*fps):Math.round(index*duration*.12);
    return Math.max(0,Math.min(Math.max(0,duration-4),start));
  });
}
