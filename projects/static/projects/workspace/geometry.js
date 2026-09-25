import { gridNearest } from "./grid.js";
export { gridNearest };

const finite = (p) => p && Number.isFinite(p.x) && Number.isFinite(p.y);
const screen = (p, t) => ({x:t.a*p.x+t.c*p.y+t.e,y:t.b*p.x+t.d*p.y+t.f});
function validCandidate(candidate) {
  if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate) || !finite(candidate.worldPoint)) return false;
  if (candidate.kind === 'NODE') return typeof candidate.canonicalKey === 'string' && /^NODE:.+$/.test(candidate.canonicalKey);
  if (candidate.kind === 'ENDPOINT') return typeof candidate.canonicalKey === 'string' && /^ENDPOINT:.+:(START|END)$/.test(candidate.canonicalKey);
  if (candidate.kind === 'INTERSECTION') {
    const keys = typeof candidate.canonicalKey === 'string' && candidate.canonicalKey.startsWith('INTERSECTION:') && candidate.canonicalKey.slice('INTERSECTION:'.length).split('|');
    return Array.isArray(keys) && keys.length === 2 && keys[0] && keys[1] && keys[0] < keys[1];
  }
  return false;
}
function choose(candidates, kinds, pointer, transform) {
  return candidates.filter(c=>validCandidate(c)&&kinds.includes(c.kind)).map(c=>{const p=screen(c.worldPoint,transform);return {...c,d:Math.hypot(p.x-pointer.x,p.y-pointer.y)}}).filter(c=>c.d<=12).sort((a,b)=>a.d-b.d||(a.canonicalKey<b.canonicalKey?-1:a.canonicalKey>b.canonicalKey?1:0))[0];
}
export function resolvePointerPoint({worldPointer,screenPointer,candidates,viewTransform,origin,ortho,gridEnabled,explicitNumeric}) {
  if(!finite(worldPointer)||!finite(screenPointer)||!finite(origin)||!['a','b','c','d','e','f'].every(k=>Number.isFinite(viewTransform?.[k]))) throw new TypeError('INVALID_RESOLVER_INPUT');
  if(explicitNumeric) return {point:{...worldPointer},snapType:null,candidateKey:null};
  const list=Array.isArray(candidates)?candidates:[];
  const object=choose(list,['NODE','ENDPOINT'],screenPointer,viewTransform);
  if(object) return {point:{...object.worldPoint},snapType:'NODE',candidateKey:object.canonicalKey};
  const intersection=choose(list,['INTERSECTION'],screenPointer,viewTransform);
  if(intersection) return {point:{...intersection.worldPoint},snapType:'INT',candidateKey:intersection.canonicalKey};
  let point={...worldPointer}; let horizontal=false, vertical=false;
  if(ortho){ const dx=point.x-origin.x,dy=point.y-origin.y; horizontal=Math.abs(dx)>=Math.abs(dy); vertical=!horizontal; if(horizontal)point.y=origin.y; else point.x=origin.x; }
  if(gridEnabled){ if(!vertical)point.x=gridNearest(point.x); if(!horizontal)point.y=gridNearest(point.y); return {point,snapType:'GRID',candidateKey:null}; }
  return {point,snapType:null,candidateKey:null};
}
