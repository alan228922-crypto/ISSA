import { gridNearest } from './grid.js';
import { worldToClient } from './coordinate-space.js';
export { gridNearest };
const finite=p=>p&&Number.isFinite(p.x)&&Number.isFinite(p.y);
const identity={a:1,b:0,c:0,d:1,e:0,f:0};
const key=c=>c.nodeClientKey || c.canonicalKey || c.memberClientKeys?.join('|') || '';
function normalize(c) {
  if(!c || !finite(c.worldPoint))return null;
  if(c.kind==='NODE' && typeof c.nodeClientKey==='string' && c.nodeClientKey)return c;
  if(c.kind==='NODE' && typeof c.canonicalKey==='string' && /^NODE:.+$/.test(c.canonicalKey))return {...c,nodeClientKey:c.canonicalKey.slice(5)};
  if(c.kind==='ENDPOINT' && typeof c.canonicalKey==='string' && /^ENDPOINT:.+:(START|END)$/.test(c.canonicalKey))return c;
  const keys=c.memberClientKeys || (typeof c.canonicalKey==='string'&&c.canonicalKey.startsWith('INTERSECTION:')?c.canonicalKey.slice(13).split('|'):null);
  if(c.kind==='INTERSECTION'&&Array.isArray(keys)&&keys.length===2&&keys.every(k=>typeof k==='string'&&k)&&keys[0]<keys[1])return {...c,memberClientKeys:keys};
  return null;
}
export function resolvePointerPoint(input) {
  const {worldPointer,origin,ortho,gridEnabled,explicitNumeric}=input;
  const legacy=!input.coordinates;
  const client=input.clientPointer || input.screenPointer;
  const coordinates=input.coordinates || {svgToClient:identity,worldToSvg:input.viewTransform};
  if(!finite(worldPointer)||!finite(client)||(origin!=null&&!finite(origin)))throw new TypeError('INVALID_RESOLVER_INPUT');
  let axis=null,point={...worldPointer};
  if(!explicitNumeric&&ortho&&origin){axis=Math.abs(point.x-origin.x)>=Math.abs(point.y-origin.y)?'HORIZONTAL':'VERTICAL';point[axis==='HORIZONTAL'?'y':'x']=origin[axis==='HORIZONTAL'?'y':'x'];}
  const result=(kind,p,c={})=>{
    const presentation={point:{...p},snapType:kind==='INTERSECTION'?'INT':['NODE','GRID'].includes(kind)?kind:null,candidateKey:kind==='NODE'?(c.canonicalKey||`NODE:${c.nodeClientKey}`):kind==='INTERSECTION'?`INTERSECTION:${c.memberClientKeys.join('|')}`:null};
    // Preserve the pre-existing pure-helper interface, not a second resolver.
    if(legacy)return presentation;
    return {kind,worldPoint:{...p},axis,...(c.nodeClientKey?{nodeClientKey:c.nodeClientKey}:{}),...(c.memberClientKeys?{memberClientKeys:c.memberClientKeys}:{}),...presentation};
  };
  if(explicitNumeric)return result('PRECISE',worldPointer);
  const list=(input.candidates||[]).map(normalize).filter(Boolean).filter(c=>!axis||c.worldPoint[axis==='HORIZONTAL'?'y':'x']===origin[axis==='HORIZONTAL'?'y':'x']);
  for(const kinds of [['NODE','ENDPOINT'],['INTERSECTION']]){
    const hits=list.filter(c=>kinds.includes(c.kind)).map(c=>{const p=worldToClient(c.worldPoint,coordinates);return {...c,d:Math.hypot(p.x-client.x,p.y-client.y)}}).filter(c=>c.d<=(legacy?12:10)).sort((a,b)=>a.d-b.d||key(a).localeCompare(key(b)));
    if(hits.length){const c=hits[0];if(!legacy&&c.kind==='NODE'&&hits.some(other=>other.nodeClientKey!==c.nodeClientKey&&other.worldPoint.x===c.worldPoint.x&&other.worldPoint.y===c.worldPoint.y)){const e=new Error('这里有多个位置相同的旧模型节点，请明确选择节点。');e.code='AMBIGUOUS_NODE_IDENTITY';throw e;}return result(c.kind==='ENDPOINT'?'NODE':c.kind,c.worldPoint,c);}
  }
  if(gridEnabled){if(axis!=='VERTICAL')point.x=gridNearest(point.x);if(axis!=='HORIZONTAL')point.y=gridNearest(point.y);return result('GRID',point);}
  return result('FREE',point);
}
