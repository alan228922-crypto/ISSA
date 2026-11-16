// Dedicated readonly SVG renderer. No editor, Draft, selection or mechanics imports.
const NS = 'http://www.w3.org/2000/svg';
const finite = Number.isFinite;
const node = (tag, attributes = {}, text = null) => {
  const result = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (typeof value === 'number' && !finite(value)) throw new RangeError('Invalid display coordinate');
    result.setAttribute(key, String(value));
  }
  if (text !== null) result.textContent = text;
  return result;
};

export function reactionDisplayComponents(reactions, calibration) {
  if (!Array.isArray(reactions) || reactions.some(row => !finite(row.rx_N) || !finite(row.ry_N))) return [];
  let reference = 0;
  for (const row of reactions) reference = Math.max(reference, Math.abs(row.rx_N), Math.abs(row.ry_N));
  if (reference === 0) return [];
  const result = [];
  for (const row of reactions) for (const [component, value] of [['Rx', row.rx_N], ['Ry', row.ry_N]]) {
    if (value === 0) continue;
    const lengthPx = Math.max(calibration.reactionMinPx, Math.min(calibration.reactionMaxPx,
      calibration.reactionMaxPx * (Math.abs(value) / reference)));
    result.push({nodeId: row.analysis_node_id, component, value, lengthPx,
      dx: component === 'Rx' ? Math.sign(value) * lengthPx : 0,
      dy: component === 'Ry' ? -Math.sign(value) * lengthPx : 0});
  }
  return result;
}

export function displacedAnalysisNodes(nodes, alpha) {
  if (!Array.isArray(nodes) || !finite(alpha) || alpha < 1) return null;
  const result = [];
  for (const row of nodes) {
    if (!finite(row.x_mm) || !finite(row.y_mm) || !finite(row.displacement?.ux_mm) || !finite(row.displacement?.uy_mm)) return null;
    const x = row.x_mm + alpha * row.displacement.ux_mm, y = row.y_mm + alpha * row.displacement.uy_mm;
    if (!finite(x) || !finite(y)) return null;
    result.push({...row, x_mm: x, y_mm: y});
  }
  return result;
}

export function fitAnalysisVisualization(nodes, width, height, calibration) {
  if (!nodes.length || !finite(width) || !finite(height) || width <= 0 || height <= 0) return null;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const row of nodes) {
    if (!finite(row.x_mm) || !finite(row.y_mm)) return null;
    minX = Math.min(minX, row.x_mm); maxX = Math.max(maxX, row.x_mm);
    minY = Math.min(minY, row.y_mm); maxY = Math.max(maxY, row.y_mm);
  }
  const dx = maxX - minX, dy = maxY - minY;
  if (!finite(dx) || !finite(dy) || (dx === 0 && dy === 0)) return null;
  const padding = Math.min(calibration.reactionMaxPx + calibration.labelOffsetPx + calibration.labelRailGapPx, width * .2, height * .2);
  const sx = dx > 0 ? (width - 2 * padding) / dx : Infinity;
  const sy = dy > 0 ? (height - 2 * padding) / dy : Infinity;
  const scale = Math.min(sx, sy);
  if (!finite(scale) || scale <= 0) return null;
  return {scale, originX: minX, originY: maxY,
    panX: padding + (width - 2 * padding - dx * scale) / 2,
    panY: padding + (height - 2 * padding - dy * scale) / 2};
}

const screenPoint = (row, transform) => ({
  x: (row.x_mm - transform.originX) * transform.scale + transform.panX,
  y: (transform.originY - row.y_mm) * transform.scale + transform.panY,
});

export function renderAnalysisVisualization(svg, view, {layers, viewTransform, alpha = null, selected = null} = {}) {
  svg.replaceChildren();
  if (!view?.available) return {available: false, overflow: false};
  const {width, height} = svg.getBoundingClientRect();
  if (!(width > 0 && height > 0)) return {available: false, hidden: true, overflow: false};
  const requestedDeformation = layers?.deformation === true;
  const amplification = alpha ?? view.deformation?.alpha;
  const displaced = requestedDeformation && view.deformation?.available && finite(amplification) && amplification >= 1 && amplification <= view.calibration.maxAlpha ? displacedAnalysisNodes(view.nodes, amplification) : null;
  const deformationOn = Boolean(displaced);
  const transform = viewTransform || fitAnalysisVisualization(displaced ? [...view.nodes, ...displaced] : view.nodes, width, height, view.calibration);
  if (!transform) return {available: false, overflow: false};
  const points = new Map(view.nodes.map(row => [row.analysis_node_id, screenPoint(row, transform)]));
  const primaryPoints = displaced ? new Map(displaced.map(row => [row.analysis_node_id, screenPoint(row, transform)])) : points;
  if ([...points.values(), ...primaryPoints.values()].some(p => !finite(p.x) || !finite(p.y))) return {available: false, overflow: false};
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.append(node('title', {}, '保存分析的只读结构视图'));
  const forceStyle=segment=>{
    if(layers?.forceStates===false||!view.forceStatesAvailable)return {};
    const state=view.segmentStates.get(segment.analysis_segment_id);
    return state==='TENSION'?{stroke:'#b91c1c'}:state==='COMPRESSION'?{stroke:'#1d4ed8','stroke-dasharray':'10 5'}
      :state==='ZERO_FORCE'?{stroke:'#64748b','stroke-dasharray':'2 4'}:{stroke:'#7e22ce','stroke-dasharray':'10 3 2 3'};
  };
  const geometry = node('g', {'data-av01-original-layer': '', 'pointer-events': 'none', ...(deformationOn ? {'data-av01-ghost': '', opacity: .45} : {})});
  for (const segment of view.segments) {
    const a = points.get(segment.start_analysis_node_id), b = points.get(segment.end_analysis_node_id);
    geometry.append(node('line', {'data-av01-original-segment': '', x1: a.x, y1: a.y, x2: b.x, y2: b.y,
      stroke: '#475569', 'stroke-width': deformationOn ? view.calibration.ghostStrokePx : 2, ...(deformationOn ? {'stroke-dasharray': '5 5'} : forceStyle(segment))}));
  }
  for (const point of points.values()) geometry.append(node('circle', {cx: point.x, cy: point.y, r: deformationOn ? 2.5 : 4, fill: 'white', stroke: 'var(--brand, #183c51)', 'stroke-width':1.6}));
  svg.append(geometry);
  if (deformationOn) {
    const primary = node('g', {'data-av01-deformed-layer': '', 'pointer-events': 'none'});
    for (const segment of view.segments) {
      const a = primaryPoints.get(segment.start_analysis_node_id), b = primaryPoints.get(segment.end_analysis_node_id);
      primary.append(node('line', {'data-av01-deformed-segment': '', 'data-analysis-segment': segment.analysis_segment_id,
        x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: 'var(--brand, #183c51)', 'stroke-width': 2.4, ...forceStyle(segment)}));
    }
    for (const [id, point] of primaryPoints) primary.append(node('circle', {'data-av01-displaced-node': '',
      'data-analysis-node': id, cx: point.x, cy: point.y, r: 4, fill: 'white', stroke:'var(--brand, #183c51)', 'stroke-width':1.6}));
    svg.append(primary);
    svg.append(node('text', {x: 8, y: 8, 'font-size': 11, 'dominant-baseline': 'hanging', fill: 'var(--brand, #183c51)', 'data-av01-shape-legend': ''}, '原始结构（浅灰虚线） / 变形结构（主线）'));
  }
  const guides=node('g',{'data-av01-guides':'','pointer-events':'none',stroke:'var(--control, #7f949d)','stroke-width':.8,fill:'none'});
  const original=[...points.values()],xs=view.nodes.map(n=>n.x_mm),ys=view.nodes.map(n=>n.y_mm);
  const rangeX=Math.max(...xs)-Math.min(...xs),rangeY=Math.max(...ys)-Math.min(...ys);
  if(!deformationOn){
    const left=Math.min(...original.map(p=>p.x)),right=Math.max(...original.map(p=>p.x)),top=Math.min(...original.map(p=>p.y)),bottom=Math.max(...original.map(p=>p.y));
    if(finite(rangeX)&&rangeX>0){guides.append(node('path',{d:`M${left} ${height-16}H${right} M${left-3} ${height-12}l6 -8 M${right-3} ${height-12}l6 -8`}));guides.append(node('text',{'data-av01-dimension':'x',x:(left+right)/2,y:height-23,'text-anchor':'middle','font-size':10,'font-family':'var(--mono, monospace)',fill:'var(--muted, #526570)',stroke:'none'},`${view.format(rangeX)} mm`));}
    if(finite(rangeY)&&rangeY>0){guides.append(node('path',{d:`M${width-16} ${top}V${bottom} M${width-20} ${top+3}l8 -6 M${width-20} ${bottom+3}l8 -6`}));guides.append(node('text',{'data-av01-dimension':'y',transform:`translate(${width-24} ${(top+bottom)/2}) rotate(-90)`,'text-anchor':'middle','font-size':10,'font-family':'var(--mono, monospace)',fill:'var(--muted, #526570)',stroke:'none'},`${view.format(rangeY)} mm`));}
  }
  const axes=node('g',{'data-av01-direction':'',transform:`translate(24 ${height-38})`,stroke:'var(--text, #172d39)','stroke-width':1,fill:'var(--text, #172d39)','pointer-events':'none','aria-label':'方向：X向右，Y向上；非模型原点'});
  axes.append(node('path',{'data-av01-axis':'x',d:'M0 0H30',fill:'none'}),node('path',{'data-av01-axis':'y',d:'M0 0V-30',fill:'none'}),node('path',{d:'M30 0L24 -2.5V2.5Z M0 -30L-2.5 -24H2.5Z',stroke:'none'}),node('circle',{r:2,stroke:'none'}),node('text',{x:35,y:3,'font-size':10,stroke:'none'},'X'),node('text',{x:-3,y:-36,'font-size':10,stroke:'none'},'Y'));
  guides.append(axes);svg.append(guides);
  const hitLayer=node('g',{'data-av01-hit-layer':''});
  const hit=(kind,id,shape)=>{
    const ref={kind,id};if(!view.objects?.has(JSON.stringify([kind,id])))return;
    const chosen=selected?.kind===kind&&selected?.id===id;
    const target=node('g',{'data-av01-target':'','data-object-kind':kind,'data-object-id':id,'pointer-events':'all',...(chosen?{'data-av01-selected':''}:{})});
    target.append(shape);
    if(shape.tagName==='line')target.append(node('circle',{cx:(Number(shape.getAttribute('x1'))+Number(shape.getAttribute('x2')))/2,cy:(Number(shape.getAttribute('y1'))+Number(shape.getAttribute('y2')))/2,r:7,fill:'transparent'}));
    // Match visible paint order: reaction arrows are above structural glyphs.
    hitLayer.append(target);
  };
  for(const segment of view.segments){const a=primaryPoints.get(segment.start_analysis_node_id),b=primaryPoints.get(segment.end_analysis_node_id);
    if(selected?.kind==='ANALYSIS_SEGMENT'&&selected.id===segment.analysis_segment_id)svg.append(node('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:'var(--accent, #0c6672)','stroke-width':7,opacity:.13,'pointer-events':'none'}));
    hit('ANALYSIS_SEGMENT',segment.analysis_segment_id,node('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:'transparent','stroke-width':14}));}
  for(const [id,p] of primaryPoints){
    if(selected?.kind==='ANALYSIS_NODE'&&selected.id===id)svg.append(node('circle',{cx:p.x,cy:p.y,r:8,fill:'none',stroke:'var(--accent, #0c6672)','stroke-width':2,'pointer-events':'none'}));
    hit('ANALYSIS_NODE',id,node('circle',{cx:p.x,cy:p.y,r:9,fill:'transparent'}));}
  const supportCounts=new Map(),supportPositions=new Map();
  for(const row of view.supports)supportCounts.set(row.analysis_node_id,(supportCounts.get(row.analysis_node_id)||0)+1);
  for(const support of view.supports){const p=points.get(support.analysis_node_id);if(!p)continue;
    const index=supportPositions.get(support.analysis_node_id)||0;supportPositions.set(support.analysis_node_id,index+1);
    const downward=view.reactionsAvailable&&layers?.reactions!==false&&view.reactions.some(row=>row.analysis_node_id===support.analysis_node_id&&row.ry_N<0);
    const offset=supportCounts.get(support.analysis_node_id)>1||downward?(index%2?-1:1)*(Math.floor(index/2)+1)*view.calibration.supportGapPx:0;
    const chosen=selected?.kind==='SUPPORT'&&selected.id===support.support_id;
    const stroke=chosen?'var(--accent, #0c6672)':'var(--brand, #183c51)',fill=chosen?'var(--selected, #e1eff2)':'#fff';
    const roller=support.support_type==='ROLLER'&&['X','Y'].includes(support.restrained_axis);
    const glyph=node('g',{transform:`translate(${p.x+offset} ${p.y})${roller&&support.restrained_axis==='X'?' rotate(-90)':''}`});
    if(support.support_type==='PINNED'||roller){
      glyph.append(node('line',{x1:0,y1:4,x2:0,y2:9,stroke,'stroke-width':1.5}));
      glyph.append(node('polygon',{points:'0,9 -13,27 13,27',fill,stroke,'stroke-width':1.5}));
      if(roller)for(const x of [-8,8])glyph.append(node('circle',{cx:x,cy:31,r:2.5,fill,stroke,'stroke-width':1.5,'data-av01-support-roller':''}));
      const ground=roller?35:30;
      glyph.append(node('line',{x1:-19,y1:ground,x2:19,y2:ground,stroke,'stroke-width':1.5,'data-av01-support-ground':''}));
      for(let x=-19;x<17;x+=6)glyph.append(node('line',{x1:x,y1:ground+5,x2:x+5,y2:ground,stroke,'stroke-width':1,'pointer-events':'none'}));
    }else glyph.append(node('rect',{x:-5,y:12,width:10,height:10,fill,stroke,'stroke-width':2}));
    const linked=node('g');
    if(offset)linked.append(node('line',{x1:p.x,y1:p.y,x2:p.x+offset,y2:p.y+9,stroke:'var(--control, #7f949d)','stroke-width':1,'pointer-events':'none','data-av01-support-anchor':''}));
    linked.append(glyph);hit('SUPPORT',support.support_id,linked);}
  svg.append(hitLayer);
  let overflow = false;
  // Reserve fixed notices before placing force labels; a later opaque notice
  // must never silently cover a successfully placed engineering value.
  const occupied = [],pendingLabels=[];
  const frame=svg.getBoundingClientRect(),clearance=view.calibration.labelClearancePx;
  const boxOf=el=>{const r=el.getBoundingClientRect();return {x:r.left-frame.left-clearance,y:r.top-frame.top-clearance,width:r.width+2*clearance,height:r.height+2*clearance};};
  const overlaps=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
  const crosses=(r,line)=>{
    const x=Number(line.getAttribute('x1')),y=Number(line.getAttribute('y1')),dx=Number(line.getAttribute('x2'))-x,dy=Number(line.getAttribute('y2'))-y;
    let lo=0,hi=1;
    for(const [p,q] of [[-dx,x-r.x],[dx,r.x+r.width-x],[-dy,y-r.y],[dy,r.y+r.height-y]]){
      if(p===0){if(q<0)return false;continue;}
      const u=q/p;if(p<0)lo=Math.max(lo,u);else hi=Math.min(hi,u);if(lo>hi)return false;
    }
    return true;
  };
  let symbolBoxes=[];
  const structuralLines=[...svg.querySelectorAll('[data-av01-original-segment],[data-av01-deformed-segment]')];
  occupied.push({x:0,y:Math.max(0,height-86),width:70,height:86});
  if(!deformationOn)occupied.push({x:0,y:Math.max(0,height-36),width,height:36},{x:Math.max(0,width-38),y:0,width:38,height});
  if(deformationOn) occupied.push({x:0,y:0,width,height:26});
  if(requestedDeformation) occupied.push({x:0,y:Math.max(0,height-50),width,height:50});
  const placeLabel = (anchor, text, kind='reaction') => {
    const label = node('text', {[`data-av01-${kind}-label`]: '', 'font-size': 11, 'font-family':'var(--mono, monospace)', 'dominant-baseline': 'hanging', fill: kind==='load'?'var(--load, #b45309)':'var(--reaction, #15803d)'}, text);
    svg.append(label);
    const labelWidth = label.getComputedTextLength(), labelHeight = 17;
    const offset = view.calibration.labelOffsetPx;
    const candidates = [{x: anchor.x + offset, y: anchor.y - 24}, {x: anchor.x + offset, y: anchor.y + offset},
      {x: anchor.x - labelWidth - offset, y: anchor.y - 24}];
    for (let y = 8; y + labelHeight < height; y += labelHeight + view.calibration.labelRailGapPx)
      candidates.push({x: width - labelWidth - 8, y},{x:8,y});
    const position = candidates.find(p => p.x >= 4 && p.y >= 4 && p.x + labelWidth <= width - 4 && p.y + labelHeight <= height - 4
      && !symbolBoxes.some(r=>overlaps({x:p.x,y:p.y,width:labelWidth,height:labelHeight},r))
      && !structuralLines.some(line=>crosses({x:p.x-clearance,y:p.y-clearance,width:labelWidth+2*clearance,height:labelHeight+2*clearance},line))
      && occupied.every(r => p.x + labelWidth + 4 < r.x || r.x + r.width + 4 < p.x || p.y + labelHeight + 3 < r.y || r.y + r.height + 3 < p.y));
    if (!position) { label.remove(); overflow = true; return; }
    occupied.push({...position, width: labelWidth, height: labelHeight});
    label.setAttribute('x', position.x); label.setAttribute('y', position.y);
    svg.insertBefore(node('line', {x1: anchor.x, y1: anchor.y, x2: position.x, y2: position.y + labelHeight / 2,
      stroke: 'var(--control, #7f949d)', 'stroke-width': .7, 'data-av01-label-leader': '', 'pointer-events': 'none'}), label);
  };
  if (layers?.reactions !== false && view.reactionsAvailable) {
    const group = node('g', {'data-av01-reaction-layer': '', 'pointer-events': 'none'});
    svg.append(group);
    for (const arrow of reactionDisplayComponents(view.reactions, view.calibration)) {
      const p = points.get(arrow.nodeId), end = {x: p.x + arrow.dx, y: p.y + arrow.dy};
      const dx = arrow.dx / arrow.lengthPx, dy = arrow.dy / arrow.lengthPx;
      const glyph = node('g', {'data-av01-reaction': '', 'data-analysis-node': arrow.nodeId,
        'data-component': arrow.component, 'data-value': arrow.value, 'pointer-events': 'none'});
      glyph.append(node('line', {x1: p.x, y1: p.y, x2: end.x, y2: end.y, stroke: 'var(--reaction, #15803d)', 'stroke-width': 1.8}));
      glyph.append(node('polygon', {points: `${end.x},${end.y} ${end.x - 8*dx + 3.2*dy},${end.y - 8*dy - 3.2*dx} ${end.x - 8*dx - 3.2*dy},${end.y - 8*dy + 3.2*dx}`, fill: 'var(--reaction, #15803d)'}));
      glyph.append(node('circle', {cx: p.x, cy: p.y, r: 4, fill: 'white', stroke: 'var(--reaction, #15803d)'}));
      group.append(glyph);
      hit('ANALYSIS_NODE',arrow.nodeId,node('line',{x1:p.x,y1:p.y,x2:end.x,y2:end.y,stroke:'transparent','stroke-width':12,'stroke-linecap':'round'}));
      pendingLabels.push([p,`${view.labels.analysisNode(arrow.nodeId)} · ${arrow.component} = ${arrow.value > 0 ? '+' : ''}${view.format(arrow.value)} N${Math.abs(arrow.value)<.001?'（极小非零值）':''}`]);
    }
  }
  if(layers?.loads!==false&&view.loadsAvailable) {
    const group=node('g',{'data-av01-load-layer':'','pointer-events':'none'});svg.append(group);
    // Reuse display-only normalization, preserving every saved load row independently.
    const displayRows=view.loads.map(row=>({analysis_node_id:row.load_id,rx_N:row.fx_N,ry_N:row.fy_N}));
    const rows=new Map(view.loads.map(row=>[row.load_id,row]));
    const forceBoxes=[...svg.querySelectorAll('[data-av01-reaction],[data-av01-target][data-object-kind="SUPPORT"]')].map(boxOf);
    for(const arrow of reactionDisplayComponents(displayRows,view.calibration)) {
      const row=rows.get(arrow.nodeId),p=points.get(row.analysis_node_id);
      const dx=arrow.dx/arrow.lengthPx,dy=arrow.dy/arrow.lengthPx;
      let display=p,placed=false;
      for(const lane of [0,...Array.from({length:12},(_,i)=>(i%2?-1:1)*(Math.floor(i/2)+1))]){
        const shift=lane*view.calibration.forceLaneGapPx,candidate={x:p.x-dy*shift,y:p.y+dx*shift};
        const r={x:Math.min(candidate.x,candidate.x-arrow.dx)-clearance,y:Math.min(candidate.y,candidate.y-arrow.dy)-clearance,width:Math.abs(arrow.dx)+2*clearance,height:Math.abs(arrow.dy)+2*clearance};
        if(r.x>=0&&r.y>=0&&r.x+r.width<=width&&r.y+r.height<=height&&!forceBoxes.some(box=>overlaps(r,box))){display=candidate;placed=true;break;}
      }
      if(!placed)overflow=true;
      const start={x:display.x-arrow.dx,y:display.y-arrow.dy};
      const component=arrow.component==='Rx'?'Fx':'Fy';
      const glyph=node('g',{'data-av01-load':'','data-load-id':row.load_id,'data-component':component,'data-value':arrow.value,'pointer-events':'none'});
      glyph.append(node('line',{x1:start.x,y1:start.y,x2:display.x,y2:display.y,stroke:'var(--load, #b45309)','stroke-width':1.8}));
      glyph.append(node('polygon',{points:`${display.x},${display.y} ${display.x-8*dx+3.2*dy},${display.y-8*dy-3.2*dx} ${display.x-8*dx-3.2*dy},${display.y-8*dy+3.2*dx}`,fill:'var(--load, #b45309)'}));
      group.append(glyph);forceBoxes.push(boxOf(glyph));
      if(display!==p)group.append(node('line',{x1:display.x,y1:display.y,x2:p.x,y2:p.y,stroke:'var(--control, #7f949d)','stroke-width':1,'data-av01-load-anchor':'','data-load-id':row.load_id}));
      pendingLabels.push([start,`${view.labels.label('NODE_LOAD',row.load_id)} · ${component} = ${arrow.value>0?'+':''}${view.format(arrow.value)} N${Math.abs(arrow.value)<.001?'（极小非零值）':''}`,'load']);
    }
  }
  for(const id of view.maximumCandidates || []) {
    const p=primaryPoints.get(id);
    svg.append(node('circle',{'data-av01-maximum':'',cx:p.x,cy:p.y,r:7,fill:'none',stroke:'#6b21a8','stroke-width':1.5,'pointer-events':'none'}));
  }
  symbolBoxes=[...svg.querySelectorAll('[data-av01-target][data-object-kind="SUPPORT"],[data-av01-reaction],[data-av01-load],[data-av01-maximum]')].map(boxOf);
  for(const args of pendingLabels)placeLabel(...args);
  if (requestedDeformation) {
    const notice = node('g', {'data-av01-scale': '', 'pointer-events': 'none', ...(deformationOn ? {'data-alpha': amplification} : {})});
    const lines = [];
    if (!deformationOn) lines.push('变形图暂不可用；显示原始结构。');
    else {
      let shown = view.format(amplification);
      if (amplification > 1 && Number(shown) === 1) shown = String(amplification);
      lines.push(amplification === 1 ? '变形显示倍率 ×1。数值仍为实际分析位移。' : `变形显示已放大 ${shown}×；数值仍为实际分析位移。`);
      if (view.deformation.zero) lines.push('本次节点位移均为 0 mm。');
      else if (amplification === view.calibration.maxAlpha && view.deformation.maximumMm * amplification * transform.scale < view.calibration.tinyVisiblePx)
        lines.push('变形已达到显示放大上限，仍不易辨认；请查看实际位移数值。');
    }
    const size = lines.length * 18 + 10;
    notice.append(node('rect', {x: 2, y: height-size, width: Math.max(0,width-4), height: size-2, fill: '#ffffff', opacity: .96}));
    lines.forEach((text,index) => notice.append(node('text', {x: 8, y: height-size+5+index*18, 'font-size': 12, 'dominant-baseline': 'hanging', fill: 'var(--text, #172d39)'}, text)));
    svg.append(notice);
  }
  return {available: true, overflow, transform, deformationOn, alpha: deformationOn ? amplification : null};
}
