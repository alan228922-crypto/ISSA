import { clientToWorld,worldToClient } from './coordinate-space.js';

// Immutable Draft identity owns this read-only discovery cache, never topology.
const cache=new WeakMap();
const finite=p=>p&&Number.isFinite(p.x)&&Number.isFinite(p.y);
const bounds=points=>({minX:Math.min(...points.map(p=>p.x)),maxX:Math.max(...points.map(p=>p.x)),minY:Math.min(...points.map(p=>p.y)),maxY:Math.max(...points.map(p=>p.y))});
const overlaps=(a,b)=>a.minX<=b.maxX&&a.maxX>=b.minX&&a.minY<=b.maxY&&a.maxY>=b.minY;
function tree(rows){
  if(!rows.length)return null;
  const box={minX:Infinity,maxX:-Infinity,minY:Infinity,maxY:-Infinity};
  for(const row of rows)for(const field of Object.keys(box))box[field]=(field.startsWith('min')?Math.min:Math.max)(box[field],row.box[field]);
  if(rows.length<=8)return {box,rows};
  const axis=box.maxX-box.minX>=box.maxY-box.minY?'X':'Y';
  const sorted=[...rows].sort((a,b)=>(a.box[`min${axis}`]+a.box[`max${axis}`])-(b.box[`min${axis}`]+b.box[`max${axis}`]));
  const middle=Math.floor(sorted.length/2);
  return {box,left:tree(sorted.slice(0,middle)),right:tree(sorted.slice(middle))};
}
function queryTree(root,box,results,diagnostics,field){
  if(!root||!overlaps(root.box,box))return;
  if(root.rows){for(const row of root.rows){if(diagnostics)diagnostics[field]=(diagnostics[field]||0)+1;if(overlaps(row.box,box))results.push(row);}return;}
  queryTree(root.left,box,results,diagnostics,field);queryTree(root.right,box,results,diagnostics,field);
}
export function getSnapCandidateIndex(draft){
  if(cache.has(draft))return cache.get(draft);
  const nodes=new Map((draft.nodes||[]).filter(n=>typeof n.client_key==='string'&&n.client_key&&finite({x:n.x_mm,y:n.y_mm})).map(n=>[n.client_key,{x:n.x_mm,y:n.y_mm}]));
  const nodeRows=[...nodes].map(([key,point])=>({key,point,box:bounds([point])}));
  const segments=(draft.physical_members||[]).flatMap(m=>{
    const start=nodes.get(m.start_node_client_key),end=nodes.get(m.end_node_client_key);
    return typeof m.client_key==='string'&&m.client_key&&start&&end&&!(start.x===end.x&&start.y===end.y)?[{key:m.client_key,start,end,box:bounds([start,end])}]:[];
  });
  const result={nodes:tree(nodeRows),segments:tree(segments)};cache.set(draft,result);return result;
}
function intersection(a,b){
  const dx=a.end.x-a.start.x,dy=a.end.y-a.start.y,ex=b.end.x-b.start.x,ey=b.end.y-b.start.y,den=dx*ey-dy*ex;
  if(Math.abs(den)<1e-12)return null;
  const x=b.start.x-a.start.x,y=b.start.y-a.start.y,t=(x*ey-y*ex)/den,u=(x*dy-y*dx)/den;
  return t>=0&&t<=1&&u>=0&&u<=1?{x:a.start.x+t*dx,y:a.start.y+t*dy}:null;
}
export function querySnapCandidates(index,{clientPoint,coordinates,radiusPx=10,diagnostics=null}){
  const corners=[[-1,-1],[-1,1],[1,-1],[1,1]].map(([x,y])=>clientToWorld({x:clientPoint.x+x*radiusPx,y:clientPoint.y+y*radiusPx},coordinates));
  const box=bounds(corners),nodes=[],segments=[],hits=[];
  queryTree(index.nodes,box,nodes,diagnostics,'nodesVisited');queryTree(index.segments,box,segments,diagnostics,'segmentsVisited');
  const nearby=p=>{const client=worldToClient(p,coordinates);return Math.hypot(client.x-clientPoint.x,client.y-clientPoint.y)<=radiusPx;};
  for(const row of nodes)if(nearby(row.point))hits.push({kind:'NODE',nodeClientKey:row.key,worldPoint:row.point});
  for(let i=0;i<segments.length;i++)for(let j=i+1;j<segments.length;j++){
    if(diagnostics)diagnostics.pairsTested=(diagnostics.pairsTested||0)+1;
    const point=intersection(segments[i],segments[j]);
    if(point&&nearby(point))hits.push({kind:'INTERSECTION',memberClientKeys:[segments[i].key,segments[j].key].sort(),worldPoint:point});
  }
  return hits;
}
