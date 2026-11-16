// 只做几何投影与标注；不计算面积、形心、惯性矩或任何力学结果。
const NS = 'http://www.w3.org/2000/svg';

export function sectionView(rectangles, width, height) {
  const vertices = rectangles.flatMap(({width_mm:w,height_mm:h,center_x_mm:x=0,center_y_mm:y=0,angle_deg:a=0}) => {
    const t=a*Math.PI/180;
    return [[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]].map(([dx,dy])=>[x+dx*Math.cos(t)-dy*Math.sin(t),y+dx*Math.sin(t)+dy*Math.cos(t)]);
  });
  const xs=vertices.map(v=>v[0]),ys=vertices.map(v=>v[1]);
  const bounds={left:Math.min(...xs),right:Math.max(...xs),bottom:Math.min(...ys),top:Math.max(...ys)};
  const spanX=bounds.right-bounds.left,spanY=bounds.top-bounds.bottom;
  const scale=Math.min(Math.max(width-150,60)/spanX,Math.max(height-128,60)/spanY);
  const mx=bounds.left+spanX/2,my=bounds.bottom+spanY/2;
  const project=(x,y)=>({x:width/2-12+(x-mx)*scale,y:height/2-8-(y-my)*scale});
  return {bounds,scale,project,rectangles:rectangles.map(r=>{const p=project(r.center_x_mm||0,r.center_y_mm||0);return {x:p.x,y:p.y,width:r.width_mm*scale,height:r.height_mm*scale,angle:-(r.angle_deg||0)};})};
}

function element(parent,tag,attributes,content) {
  const node=document.createElementNS(NS,tag);
  for(const [key,value] of Object.entries(attributes))node.setAttribute(key,String(value));
  if(content!==undefined)node.textContent=content;
  parent.append(node);return node;
}
function line(parent,x1,y1,x2,y2,extra={}) {return element(parent,'line',{x1,y1,x2,y2,stroke:'var(--control,#7f949d)','stroke-width':.8,'vector-effect':'non-scaling-stroke',...extra});}
function text(parent,x,y,value,extra={}) {return element(parent,'text',{x,y,fill:'var(--muted,#526570)','font-size':11,'font-family':'var(--mono,monospace)','data-graphic-label':'',...extra},value);}

export function drawSection(svg,rectangles,properties=null,rectangle=false) {
  svg.replaceChildren();
  if(!rectangles.length)return;
  const width=svg.clientWidth||400,height=svg.clientHeight||300,view=sectionView(rectangles,width,height);
  if(!Number.isFinite(view.scale)||view.scale<=0)return;
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
  element(svg,'title',{},'当前输入的截面几何；计算属性由服务器提供');
  for(const [i,r] of view.rectangles.entries()) {
    const source=rectangles[i];
    element(svg,'rect',{x:r.x-r.width/2,y:r.y-r.height/2,width:r.width,height:r.height,transform:`rotate(${r.angle} ${r.x} ${r.y})`,
      fill:i%2?'var(--selected,#e1eff2)':'var(--subtle,#edf2f3)',stroke:'var(--brand,#183c51)','stroke-width':1.5,'vector-effect':'non-scaling-stroke',
      'data-section-component':i,'data-input-width-mm':source.width_mm,'data-input-height-mm':source.height_mm,'data-input-center-x-mm':source.center_x_mm||0,'data-input-center-y-mm':source.center_y_mm||0,'data-input-angle-deg':source.angle_deg||0});
  }
  const {bounds,project}=view,lt=project(bounds.left,bounds.top),rb=project(bounds.right,bounds.bottom),origin=project(0,0);
  if(origin.x>24&&origin.x<width-24)line(svg,origin.x,24,origin.x,height-44,{'stroke-dasharray':'6 3 1 3'});
  if(origin.y>24&&origin.y<height-44)line(svg,24,origin.y,width-30,origin.y,{'stroke-dasharray':'6 3 1 3'});
  const dy=rb.y+24,dx=rb.x+25;
  line(svg,lt.x,rb.y+7,lt.x,dy+5);line(svg,rb.x,rb.y+7,rb.x,dy+5);line(svg,lt.x,dy,rb.x,dy);
  for(const x of [lt.x,rb.x])line(svg,x-3,dy+3,x+3,dy-3);
  text(svg,(lt.x+rb.x)/2,dy+18,rectangle ? `b = ${rectangles[0].width_mm} mm` : `包络宽 ≈ ${Number((bounds.right-bounds.left).toPrecision(6))} mm`,{'text-anchor':'middle'});
  line(svg,rb.x+7,lt.y,dx+5,lt.y);line(svg,rb.x+7,rb.y,dx+5,rb.y);line(svg,dx,lt.y,dx,rb.y);
  for(const y of [lt.y,rb.y])line(svg,dx-3,y+3,dx+3,y-3);
  text(svg,dx+13,(lt.y+rb.y)/2,rectangle ? `h = ${rectangles[0].height_mm} mm` : `包络高 ≈ ${Number((bounds.top-bounds.bottom).toPrecision(6))} mm`,{'text-anchor':'middle',transform:`rotate(-90 ${dx+13} ${(lt.y+rb.y)/2})`});
  // 坐标方向指示与工程原点分离，偏置截面也不会误标原点位置。
  const axes=element(svg,'g',{'aria-label':'全局X向右、Y向上'});
  element(axes,'path',{d:`M16 ${height-17}v-23m-3 4 3-4 3 4M16 ${height-17}h23m-4-3 4 3-4 3`,fill:'none',stroke:'var(--muted,#526570)','stroke-width':.9});
  text(axes,43,height-13,'X',{'font-size':10});text(axes,21,height-38,'Y',{'font-size':10});
  if(properties&&Number.isFinite(properties.centroid_x_mm)&&Number.isFinite(properties.centroid_y_mm)) {
    const x=properties.centroid_x_mm,y=properties.centroid_y_mm,p=project(x,y);
    const g=element(svg,'g',{'data-section-centroid':'','data-centroid-x-mm':x,'data-centroid-y-mm':y,'aria-label':`形心 C，X ${x} mm，Y ${y} mm`});
    element(g,'circle',{cx:p.x,cy:p.y,r:4.5,fill:'var(--surface,#fff)',stroke:'var(--accent,#0c6672)','stroke-width':1.2});
    line(g,p.x-8,p.y,p.x+8,p.y,{stroke:'var(--accent,#0c6672)', 'stroke-width':1});line(g,p.x,p.y-8,p.x,p.y+8,{stroke:'var(--accent,#0c6672)', 'stroke-width':1});
    line(g,p.x+7,p.y-7,p.x+16,p.y-14);text(g,p.x+20,p.y-15,'C');
  }
}
