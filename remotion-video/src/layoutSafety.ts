export interface Rect {left:number;top:number;right:number;bottom:number}
export function outside(inner:Rect,outer:Rect,tolerance=1):boolean {
  return inner.left<outer.left-tolerance || inner.top<outer.top-tolerance || inner.right>outer.right+tolerance || inner.bottom>outer.bottom+tolerance;
}

// Browser text geometry catches actual rendered overflow, including nested spans.
export function findTextOverflow(root:HTMLElement):string[] {
  const screen=root.getBoundingClientRect();
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  const failures:string[]=[];
  let node:Node|null;
  while((node=walker.nextNode())) {
    if(!node.textContent?.trim()) continue;
    const parent=node.parentElement;
    if(!parent) continue;
    let visible=true;
    const clips:DOMRect[]=[];
    let element:HTMLElement|null=parent;
    while(element && element!==root.parentElement) {
      const css=getComputedStyle(element);
      if(css.display==='none' || css.visibility==='hidden' || Number(css.opacity)<.05) {visible=false;break;}
      if(['hidden','clip'].includes(css.overflow) || element.dataset.safeText!==undefined) clips.push(element.getBoundingClientRect());
      element=element.parentElement;
    }
    if(!visible) continue;
    const range=document.createRange();range.selectNodeContents(node);
    const rects=Array.from(range.getClientRects()).filter(rect=>rect.width>0 && rect.height>0);
    if(rects.some(rect=>outside(rect,screen,2) || clips.some(clip=>outside(rect,clip,2)))) {
      failures.push(node.textContent.trim().slice(0,100));
    }
  }
  return [...new Set(failures)];
}
