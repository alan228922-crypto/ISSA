// All viewport conversions live here. Browser client pixels are never world mm.
export class CoordinateSpaceError extends Error {
  constructor() { super('无法读取画布坐标，请重新选择绘图点。'); this.code = 'INVALID_COORDINATE_SPACE'; }
}
const fields = ['a','b','c','d','e','f'];
function matrix(value) {
  if (!value || !fields.every(k => Number.isFinite(value[k])) || value.a * value.d - value.b * value.c === 0) throw new CoordinateSpaceError();
  return Object.fromEntries(fields.map(k => [k,value[k]]));
}
function transform(point, value, inverse = false) {
  const m = matrix(value);
  if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) throw new CoordinateSpaceError();
  if (!inverse) return {x:m.a*point.x+m.c*point.y+m.e,y:m.b*point.x+m.d*point.y+m.f};
  const det=m.a*m.d-m.b*m.c, x=point.x-m.e, y=point.y-m.f;
  return {x:(m.d*x-m.c*y)/det,y:(-m.b*x+m.a*y)/det};
}
export function readCoordinateSpace(svg, viewTransform = null) {
  const world = svg.querySelector('[data-world-layer]');
  return {svgToClient:matrix(svg.getScreenCTM?.()),worldToSvg:matrix(viewTransform || world?.transform?.baseVal?.consolidate()?.matrix)};
}
export const clientPointToSvgLocal=(p,s)=>transform(p,s.svgToClient,true);
export const svgLocalToWorld=(p,s)=>transform(p,s.worldToSvg,true);
export const worldToSvgLocal=(p,s)=>transform(p,s.worldToSvg);
export const svgLocalToClient=(p,s)=>transform(p,s.svgToClient);
export const worldToClient=(p,s)=>svgLocalToClient(worldToSvgLocal(p,s),s);
export const clientToWorld=(p,s)=>svgLocalToWorld(clientPointToSvgLocal(p,s),s);
export function clientDeltaToSvgLocal(from,to,space) {
  const a=clientPointToSvgLocal(from,space),b=clientPointToSvgLocal(to,space);
  return {x:b.x-a.x,y:b.y-a.y};
}
export function visibleSvgViewport(svg,space) {
  const r=svg.getBoundingClientRect(), parent=svg.closest('.workspace-center')?.getBoundingClientRect() || r;
  const left=Math.max(r.left,parent.left,0),top=Math.max(r.top,parent.top,0);
  const right=Math.min(r.right,parent.right,window.innerWidth);
  const status=document.querySelector('#workspace-status-bar')?.getBoundingClientRect();
  // The fixed status controls can cover the lower canvas on responsive layouts.
  const statusTop=status&&status.left<right&&status.right>left&&status.top>top&&status.bottom>=Math.min(r.bottom,window.innerHeight)?status.top:Infinity;
  const bottom=Math.min(r.bottom,parent.bottom,window.innerHeight,statusTop);
  const a=clientPointToSvgLocal({x:left,y:top},space),b=clientPointToSvgLocal({x:right,y:bottom},space);
  return {left:a.x,top:a.y,width:Math.max(0,b.x-a.x),height:Math.max(0,b.y-a.y)};
}
export function cssPixelsPerWorldUnit(space) {
  const a=worldToClient({x:0,y:0},space),b=worldToClient({x:1,y:0},space);
  return Math.hypot(b.x-a.x,b.y-a.y);
}
