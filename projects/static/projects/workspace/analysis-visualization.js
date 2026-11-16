import {createStudentLabelResolver} from './labels.js';
import {fitAnalysisVisualization, renderAnalysisVisualization, displacedAnalysisNodes} from './analysis-visualization-renderer.js';

export const VISUAL_CALIBRATION = Object.freeze({reactionMinPx: 20, reactionMaxPx: 64,
  deformationTargetFraction: .05, minAlpha: 1, maxAlpha: 10000,
  labelOffsetPx: 12, labelRailGapPx: 4, labelClearancePx: 4, supportGapPx: 44, forceLaneGapPx: 18, tinyVisiblePx: 1, ghostStrokePx: 1.2, hoverDelayMs: 400});
const finite = Number.isFinite;
const ready = cap => cap?.status === 'READY';
const unavailable = () => ({available: false, nodes: [], segments: [], supports: [], loads: [], reactions: []});

export function formatVisualizationNumber(value, {exact = false} = {}) {
  if (!finite(value)) return '暂不可用';
  if (value === 0) return '0';
  if (exact) return String(value);
  if (Math.abs(value) < .001 || Math.abs(value) >= 1e6) {
    const [coefficient, exponent] = value.toExponential(5).split('e');
    return `${coefficient.replace(/\.?0+$/, '')}e${exponent}`;
  }
  return String(Number(value.toPrecision(6)));
}

export function deformationDisplayScale({nodes, maximumMm, calibration = VISUAL_CALIBRATION}) {
  const no = reason => ({available: false, alpha: null, reason});
  if (!Array.isArray(nodes) || !nodes.length || nodes.some(row => !finite(row.x_mm) || !finite(row.y_mm)
    || !finite(row.displacement?.ux_mm) || !finite(row.displacement?.uy_mm))) return no('MISSING_DISPLACEMENTS');
  if (!finite(maximumMm) || maximumMm < 0) return no('MISSING_MAXIMUM');
  if (calibration.minAlpha !== 1 || !finite(calibration.maxAlpha) || calibration.maxAlpha < 1
    || !finite(calibration.deformationTargetFraction) || calibration.deformationTargetFraction <= 0) return no('INVALID_CALIBRATION');
  let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity,hasNonzero=false;
  for(const row of nodes) {
    minX=Math.min(minX,row.x_mm);maxX=Math.max(maxX,row.x_mm);minY=Math.min(minY,row.y_mm);maxY=Math.max(maxY,row.y_mm);
    hasNonzero ||= row.displacement.ux_mm!==0 || row.displacement.uy_mm!==0;
  }
  const diagonal=Math.hypot(maxX-minX,maxY-minY);
  if(!finite(diagonal)||diagonal<=0)return no('INVALID_GEOMETRY_BOUNDS');
  if((maximumMm===0&&hasNonzero)||(maximumMm>0&&!hasNonzero))return no('CONTRADICTORY_MAXIMUM');
  let alpha=1;
  if(maximumMm>0) {
    const target=calibration.deformationTargetFraction*diagonal;
    if(!finite(target))return no('INVALID_DISPLAY_SCALE');
    // Compare bounded ratios before division, avoiding overflow for tiny Umax.
    alpha=maximumMm<=target/calibration.maxAlpha ? calibration.maxAlpha : maximumMm>=target ? 1 : target/maximumMm;
  }
  if(!finite(alpha)||alpha<1||!displacedAnalysisNodes(nodes,alpha))return no('INVALID_DISPLAY_GEOMETRY');
  return {available:true,alpha,reason:null,zero:!hasNonzero,maximumMm};
}

export function buildAnalysisVisualizationView({projection, teachingView = null, expectedContext}) {
  const p = projection?.provenance;
  if (projection?.schema_version !== 'analysis-visualization-v1' || !p || p.readonly !== true || !expectedContext
    || !['READY', 'PARTIAL'].includes(projection.status) || !ready(projection.capabilities?.geometry)) return unavailable();
  const fields = [['projectId','project_id'],['runId','analysis_run_id'],['revisionId','model_revision_id'],
    ['sourceDraftVersion','source_draft_version'],['modelHash','model_hash'],['inputHash','input_hash'],
    ['inputSchemaVersion','input_schema_version'],['resultSchemaVersion','result_schema_version']];
  if (fields.some(([a,b]) => expectedContext[a] === undefined || expectedContext[a] !== p[b])
    || !/^[a-f0-9]{64}$/i.test(p.model_hash) || !/^[a-f0-9]{64}$/i.test(p.input_hash)) return unavailable();
  const copy = structuredClone(projection);
  if (!Array.isArray(copy.nodes) || !copy.nodes.length || !Array.isArray(copy.segments) || !copy.segments.length
    || !copy.label_source || copy.nodes.some(row => typeof row.analysis_node_id !== 'string' || !finite(row.x_mm) || !finite(row.y_mm))) return unavailable();
  const ids = new Set(copy.nodes.map(row => row.analysis_node_id));
  if (ids.size !== copy.nodes.length || copy.segments.some(row => !ids.has(row.start_analysis_node_id) || !ids.has(row.end_analysis_node_id))) return unavailable();
  const reactions = Array.isArray(copy.reactions) ? copy.reactions : [];
  const expectedReactions = new Set((copy.supports || []).map(row => row.analysis_node_id));
  const reactionIds = new Set(reactions.map(row => row.analysis_node_id));
  const reactionsAvailable = ready(copy.capabilities.reactions) && reactionIds.size === reactions.length
    && reactionIds.size === expectedReactions.size && [...expectedReactions].every(id => reactionIds.has(id))
    && reactions.every(row => ids.has(row.analysis_node_id) && finite(row.rx_N) && finite(row.ry_N));
  const matchingTeaching = teachingView?.available === true && teachingView.projectId === p.project_id
    && teachingView.runId === p.analysis_run_id && teachingView.sourceDraftVersion === p.source_draft_version ? teachingView : null;
  const maximumMm = matchingTeaching?.displacement?.available === true ? matchingTeaching.displacement.maximumMm : null;
  const deformation = ready(copy.capabilities.deformation) ? deformationDisplayScale({nodes: copy.nodes, maximumMm}) : {available:false,alpha:null,reason:'SOURCE_DISPLACEMENTS_UNAVAILABLE'};
  const loads = Array.isArray(copy.loads) ? copy.loads : [];
  const loadsAvailable = ready(copy.capabilities.loads) && Array.isArray(copy.loads)
    && new Set(loads.map(row=>row.load_id)).size===loads.length
    && loads.every(row=>typeof row.load_id==='string' && ids.has(row.analysis_node_id) && finite(row.fx_N) && finite(row.fy_N));
  // Classification is supplied by M9; axial-force sign is never a substitute.
  const segmentStates = new Map();
  const segments = new Map(copy.segments.map(row=>[row.analysis_segment_id,row]));
  let forceStatesAvailable = ready(copy.capabilities.axial_forces) && Array.isArray(matchingTeaching?.members)
    && segments.size===copy.segments.length;
  for(const member of matchingTeaching?.members || []) for(const evidence of member.segments || []) {
    const segment=segments.get(evidence.analysis_member_id);
    if(!segment || segment.physical_member_id!==member.key || !finite(segment.axial_force_N)
      || segment.axial_force_N!==evidence.axial_force_N || segmentStates.has(evidence.analysis_member_id)
      || !['TENSION','COMPRESSION','ZERO_FORCE','MIXED'].includes(evidence.teaching_state)) forceStatesAvailable=false;
    segmentStates.set(evidence.analysis_member_id,evidence.teaching_state);
  }
  forceStatesAvailable &&= segmentStates.size===segments.size;
  const maximumCandidates = [];
  const candidateIds=new Set();
  for(const candidate of (matchingTeaching?.displacement?.available === true ? matchingTeaching.displacement.candidates : []) || []) {
    if(ids.has(candidate.id) && !candidateIds.has(candidate.id)) {maximumCandidates.push(candidate.id);candidateIds.add(candidate.id);}
  }
  const view = {...copy, available: true, deformation, reactionsAvailable, reactions: reactionsAvailable ? reactions : [],
    loadsAvailable, loads: loadsAvailable ? loads : [], forceStatesAvailable, segmentStates, maximumCandidates,
    labels: createStudentLabelResolver(copy.label_source), format: formatVisualizationNumber,
    calibration: VISUAL_CALIBRATION, teachingView: matchingTeaching};
  view.objects=buildObjectEvidence(view);
  return view;
}

// The one Object Evidence projection for Canvas, list, Inspector and Preview.
// References are exact saved identities; no geometry or classification inference.
const objectKey = ref => JSON.stringify([ref.kind,ref.id]);
const STATE_TEXT = Object.freeze({TENSION:'受拉',COMPRESSION:'受压',ZERO_FORCE:'近似零力',MIXED:'各分析段的受力状态不同'});
const COMPARISON_TEXT = Object.freeze({MATCH:'和预测一致',MISMATCH:'和预测不同',UNSURE:'之前选择“不确定”',NOT_COMPARABLE:'不能用单一类别直接对照'});
const SUPPORT_TEXT = Object.freeze({PINNED:'铰支座',ROLLER:'滚动支座'});
const field = (key,label,value,unit='',signed=false) => ({key,label,value,unit,signed});
function fieldText(row,exact=false) {
  if(typeof row.value==='string')return row.value;
  const value=formatVisualizationNumber(row.value,{exact});
  return finite(row.value)?`${row.signed&&row.value>0?'+':''}${value}${row.unit?' '+row.unit:''}`:value;
}
function buildObjectEvidence(view) {
  const objects=new Map(),nodes=new Map(view.nodes.map(row=>[row.analysis_node_id,row]));
  const reactions=new Map(view.reactions.map(row=>[row.analysis_node_id,row]));
  const add=(kind,id,name,fields,previewKeys,extra={})=>{
    const ref=Object.freeze({kind,id});
    objects.set(objectKey(ref),Object.freeze({ref,name,fields,preview:fields.filter(row=>previewKeys.includes(row.key)),...extra}));
  };
  const reactionFields=id=>{const r=reactions.get(id);return [field('Rx','Rx（节点合计）',r?.rx_N,'N',true),field('Ry','Ry（节点合计）',r?.ry_N,'N',true)];};
  const supportsAt=id=>view.supports.filter(row=>row.analysis_node_id===id).map(row=>view.labels.label('SUPPORT',row.support_id));
  for(const row of view.nodes) {
    const ux=row.displacement?.ux_mm,uy=row.displacement?.uy_mm;
    const magnitude=finite(ux)&&finite(uy)?Math.hypot(ux,uy):null;
    add('ANALYSIS_NODE',row.analysis_node_id,view.labels.analysisNode(row.analysis_node_id),[
      field('X','原始 X',row.x_mm,'mm'),field('Y','原始 Y',row.y_mm,'mm'),field('ux','ux',ux,'mm'),field('uy','uy',uy,'mm'),
      field('magnitude','位移大小',magnitude,'mm'),...reactionFields(row.analysis_node_id)],['X','Y','ux','uy'],
      {relatedSupports:supportsAt(row.analysis_node_id),maximumCandidate:view.maximumCandidates.includes(row.analysis_node_id)});
  }
  for(const row of view.supports) {
    if(!nodes.has(row.analysis_node_id))continue;
    const restrictions=row.support_type==='PINNED'?'X、Y':row.support_type==='ROLLER'&&['X','Y'].includes(row.restrained_axis)?row.restrained_axis:'暂不可用';
    add('SUPPORT',row.support_id,view.labels.label('SUPPORT',row.support_id),[
      field('node','所属节点',view.labels.analysisNode(row.analysis_node_id)),field('type','支座类型',SUPPORT_TEXT[row.support_type]||'暂不可用'),
      field('restrictions','受限方向',restrictions),...reactionFields(row.analysis_node_id)],['node','type','Rx','Ry'],
      {relatedSupports:supportsAt(row.analysis_node_id),aggregateReaction:true});
  }
  for(const row of view.segments) {
    const member=view.teachingView?.members?.find(item=>item.key===row.physical_member_id);
    const siblings=view.segments.filter(item=>item.physical_member_id===row.physical_member_id).map(item=>({
      name:view.labels.analysisMember(item.physical_member_id,item.analysis_segment_id),
      force:field('N','N',ready(view.capabilities.axial_forces)?item.axial_force_N:null,'N',true),
      state:view.forceStatesAvailable?STATE_TEXT[view.segmentStates.get(item.analysis_segment_id)]||'暂不可用':'暂不可用'}));
    add('ANALYSIS_SEGMENT',row.analysis_segment_id,view.labels.analysisMember(row.physical_member_id,row.analysis_segment_id),[
      field('member','所属构件',view.labels.label('PHYSICAL_MEMBER',row.physical_member_id)),
      field('N','N',ready(view.capabilities.axial_forces)?row.axial_force_N:null,'N',true),
      field('state','受力状态',view.forceStatesAvailable?STATE_TEXT[view.segmentStates.get(row.analysis_segment_id)]||'暂不可用':'暂不可用'),
      field('memberState','构件已有分类',view.forceStatesAvailable?STATE_TEXT[member?.actualState]||'暂不可用':'暂不可用'),
      field('comparison','已有预测对比',COMPARISON_TEXT[member?.comparisonStatus]||'暂不可用')],['member','N','state'],{siblings});
  }
  return objects;
}

const element = (tag, attrs = {}, text = null) => {
  const result = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) result.setAttribute(key, value);
  if (text !== null) result.textContent = text;
  return result;
};
let instanceNumber = 0;
const DEFAULT_LAYERS = Object.freeze({loads: true, reactions: true, forceStates: true, deformation: false});

export function createAnalysisVisualization({root, onRetry = () => {}}) {
  root.classList.add('av01-view','ui-controls'); root.dataset.av01Root = '';
  const icon = name => { const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('class','ui-icon');svg.setAttribute('aria-hidden','true');const use=document.createElementNS(svg.namespaceURI,'use');use.setAttribute('href',new URL(`../../ui/icons.svg#${name}`,import.meta.url).href);svg.append(use);return svg; };
  const header = element('header', {class: 'av01-header'});
  header.append(element('h3', {}, '结构视图 · 只读'));
  const zoomIn = element('button', {type:'button', 'data-av01-zoom-in':''}, '放大');
  const zoomOut = element('button', {type:'button', 'data-av01-zoom-out':''}, '缩小');zoomIn.prepend(icon('zoomIn'));zoomOut.prepend(icon('zoomOut'));header.append(zoomIn,zoomOut);
  const fit = element('button', {type: 'button', 'data-av01-fit': ''}, '适合视窗'); fit.prepend(icon('fit'));header.append(fit);
  const instanceId=++instanceNumber;
  const controls=element('div',{class:'av01-layers',role:'group','aria-label':'结构视图图层'});
  const controlRows=new Map();
  for(const [key,title] of [['loads','外部荷载'],['reactions','支座反力'],['forceStates','拉压状态'],['deformation','变形图 AUTO']]) {
    const label=element('label');const input=element('input',{type:'checkbox','data-av01-layer':key,'aria-describedby':`av01-${instanceId}-${key}-reason`});
    const reason=element('span',{'data-av01-layer-reason':key,id:`av01-${instanceId}-${key}-reason`});
    label.append(input,document.createTextNode(title),reason);controls.append(label);controlRows.set(key,{input,reason});
  }
  const retry = element('button',{type:'button','data-av01-retry':''},'重试结构视图');retry.hidden=true;header.append(retry);retry.addEventListener('click',()=>onRetry());
  const status = element('p', {'data-av01-status': '', role: 'status'});
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('data-av01-canvas', ''); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', '保存分析的只读结构视图');
  svg.setAttribute('tabindex','0');
  const wrap=element('div',{class:'av01-canvas-wrap'});
  const tooltip=element('aside',{'data-av01-hover':'',role:'tooltip',class:'av01-hover'});tooltip.hidden=true;
  wrap.append(svg,tooltip);
  const inspector=element('section',{'data-av01-evidence':'','aria-label':'所选分析证据','aria-live':'polite'});
  const diagram=element('div',{class:'av01-diagram'});diagram.append(wrap,inspector);
  const objectList=element('details',{'data-av01-object-list':''});objectList.append(element('summary',{},'选择分析对象（节点、支座、分析段）'));
  const objectGroups=new Map();
  for(const [kind,title] of [['ANALYSIS_NODE','节点'],['SUPPORT','支座'],['ANALYSIS_SEGMENT','分析段']]) {const section=element('section');section.append(element('h4',{},title));const ul=element('ul');section.append(ul);objectList.append(section);objectGroups.set(kind,ul);}
  const legend = element('p', {'data-av01-legend': '', class: 'av01-legend'}, '原始结构：灰色实线；支座反力：绿色箭头。坐标单位 mm，力单位 N。箭头长度经过显示缩放，请以标示数值为准。');
  const legendDetails=element('details',{'data-av01-legend-details':''});legendDetails.append(element('summary',{},'图例与显示说明'),legend);
  const displaySummary=element('p',{'data-av01-display-summary':'',class:'av01-display-summary'},'坐标 mm；力 N。箭头长度经过显示缩放，请以数值为准。');
  const overflow = element('p', {'data-av01-overflow': '', role: 'status'}, '部分标注请展开下方数值列表查看。'); overflow.hidden = true;
  const values = element('details', {'data-av01-values': ''});values.append(element('summary', {}, '工程数值与关联支座（完整原值）'));
  const table = element('table');const head = element('thead');const tr = element('tr');for (const text of ['节点与关联支座','Rx (N)','Ry (N)'])tr.append(element('th', {scope:'col'}, text));head.append(tr);const body=element('tbody');table.append(head,body);values.append(table);
  const exactScale = element('p', {'data-av01-exact-scale':''});exactScale.hidden=true;values.append(exactScale);
  const displacementTable=element('table',{'data-av01-displacement-values':''});const displacementHead=element('thead');const displacementHeader=element('tr');
  for(const text of ['节点','ux (mm)','uy (mm)'])displacementHeader.append(element('th',{scope:'col'},text));displacementHead.append(displacementHeader);
  const displacementBody=element('tbody');displacementTable.append(displacementHead,displacementBody);values.append(displacementTable);
  const loadTable=element('table',{'data-av01-load-values':''});const loadHead=element('thead'),loadHeader=element('tr'),loadBody=element('tbody');
  for(const text of ['荷载与作用节点','Fx (N)','Fy (N)'])loadHeader.append(element('th',{scope:'col'},text));
  loadHead.append(loadHeader);loadTable.append(loadHead,loadBody);values.append(loadTable);
  const sidebar=element('aside',{class:'av01-sidebar','aria-label':'分析结论与工程证据'});
  const conclusionSlot=element('section',{'data-av01-conclusion-slot':''});
  const layersTitle=element('h4',{},'图层');layersTitle.prepend(icon('layers'));
  const evidenceTitle=element('h4',{},'对象证据');evidenceTitle.prepend(icon('book'));
  sidebar.append(conclusionSlot,layersTitle,controls,evidenceTitle,inspector,objectList,legendDetails,values);
  diagram.prepend(sidebar);
  root.replaceChildren(header, status, diagram, displaySummary, overflow);
  let selection = null, projection = null, expectedContext = null, teachingView = null, view = null, viewTransform = null, destroyed = false;
  let layers = {...DEFAULT_LAYERS};
  let drag=null,frame=null,selected=null,visible=true,loadState=null;
  let pendingHover=null,hoverTarget=null,hoverAnchor=null,dismissedHover=null,hoverGeneration=0;
  const listButtons=new Map();
  const isVisible=()=>visible&&root.isConnected&&svg.getClientRects().length>0&&document.visibilityState!=='hidden';
  const cancelHover=(leave=false)=>{hoverGeneration++;if(pendingHover!==null)clearTimeout(pendingHover);pendingHover=null;hoverTarget=null;hoverAnchor=null;tooltip.hidden=true;tooltip.replaceChildren();if(leave)dismissedHover=null;};
  const dismissHover=()=>{const key=hoverTarget?.key;cancelHover();if(key)dismissedHover=key;};
  const recordFor=target=>{
    const hit=target?.closest?.('[data-av01-target]');if(!hit||!svg.contains(hit)||!view?.objects)return null;
    const key=objectKey({kind:hit.dataset.objectKind,id:hit.dataset.objectId}),record=view.objects.get(key);
    return record?{key,record,hit}:null;
  };
  const rowsInto=(container,fields,{exact=false,preview=false}={})=>{
    for(const row of fields){const line=element('p',{'data-av01-field':row.key,...(preview?{'data-av01-preview-field':''}:{})});
      line.append(element('span',{},`${row.label}：`),element('strong',{'data-av01-value':''},fieldText(row,exact)));
      if(!exact&&finite(row.value)&&row.value!==0&&Math.abs(row.value)<.001)line.append(document.createTextNode('（极小非零值）'));
      if(!preview&&['Rx','Ry'].includes(row.key)&&finite(row.value))line.append(document.createTextNode(row.value===0?'（零值，无方向）':row.key==='Rx'?(row.value>0?'（向右）':'（向左）'):(row.value>0?'（向上）':'（向下）')));
      container.append(line);
    }
  };
  const renderEvidence=()=>{
    const oldDetails=inspector.querySelector('[data-av01-exact]'),wasOpen=oldDetails?.open;
    const keepFocus=oldDetails?.querySelector('summary')===document.activeElement;
    inspector.replaceChildren();const record=view?.objects?.get(selected?objectKey(selected):'');
    if(!record){inspector.append(element('p',{},'请选择节点、支座或分析段，查看这次分析的工程证据。'));return;}
    inspector.append(element('h4',{},record.name),element('p',{class:'av01-evidence-note'},'图中为显示精度；完整保存值可按需展开。'));
    rowsInto(inspector,record.fields);
    if(record.relatedSupports?.length)inspector.append(element('p',{},`关联支座：${record.relatedSupports.join('、')}。`));
    if(record.aggregateReaction)inspector.append(element('p',{},'这里是该节点的合计反力，不分配到个别支座。'));
    if(record.siblings){const section=element('section');section.append(element('h5',{},'同一构件的各分析段结果'));
      for(const sibling of record.siblings)section.append(element('p',{'data-av01-sibling':''},`${sibling.name}：${fieldText(sibling.force)}；${sibling.state}。`));inspector.append(section);}
    const exact=element('details',{'data-av01-exact':''});exact.open=Boolean(wasOpen);exact.append(element('summary',{},'完整保存值'));
    rowsInto(exact,record.fields,{exact:true});
    if(record.siblings)for(const sibling of record.siblings)exact.append(element('p',{},`${sibling.name}：${fieldText(sibling.force,true)}；${sibling.state}。`));
    inspector.append(exact);if(keepFocus&&isVisible())exact.querySelector('summary').focus({preventScroll:true});
  };
  const selectObject=ref=>{if(!view?.objects?.has(objectKey(ref)))return;cancelHover();selected=ref;renderEvidence();draw();if(isVisible())sidebar.scrollTop+=inspector.getBoundingClientRect().top-sidebar.getBoundingClientRect().top-8;};
  const syncObjects=()=>{
    const objects=view?.objects||new Map();
    for(const [key,button] of listButtons)if(!objects.has(key)){button.parentElement.remove();listButtons.delete(key);}
    const positions=new Map();
    for(const [key,record] of objects){let button=listButtons.get(key);const parent=objectGroups.get(record.ref.kind);
      if(!button){button=element('button',{type:'button','data-object-kind':record.ref.kind,'data-object-id':record.ref.id});button.addEventListener('click',()=>selectObject(record.ref));const li=element('li');li.append(button);parent.append(li);listButtons.set(key,button);}
      button.textContent=record.name+(record.maximumCandidate?' · 最大位移候选':'');
      if(record.maximumCandidate)button.dataset.av01MaximumCandidate='';else delete button.dataset.av01MaximumCandidate;
      button.setAttribute('aria-pressed',String(selected&&objectKey(selected)===key));
      const index=positions.get(record.ref.kind)||0;if(parent.children[index]!==button.parentElement)parent.insertBefore(button.parentElement,parent.children[index]||null);positions.set(record.ref.kind,index+1);
    }
    objectList.hidden=!objects.size;renderEvidence();
  };
  const draw = () => {
    if (destroyed) return;
    cancelHover();
    body.replaceChildren();displacementBody.replaceChildren();loadBody.replaceChildren();exactScale.hidden=true;
    for(const [key,{input,reason}] of controlRows) {
      const available=Boolean(view?.available && (key==='deformation'?view.deformation.available:view[`${key}Available`]));
      input.disabled=!available;input.checked=available&&layers[key];reason.textContent=available?'':'（暂不可用）';reason.hidden=available;
    }
    if (!view?.available) { svg.replaceChildren();legend.textContent='';legend.hidden=true;legendDetails.hidden=true;displaySummary.hidden=true;retry.hidden=loadState!=='ERROR';status.textContent=({LOADING:'正在载入所选分析的结构视图…',ERROR:'结构视图暂时无法载入，请重试。',DENIED:'无权查看这次分析，结构视图已清除。',UNAVAILABLE:'这次分析的结构视图暂不可用，请查看已有数值资料。'})[loadState]||(projection?'这次分析的结构视图暂不可用，请查看已有数值资料。':'请选择分析记录。');root.dataset.av01Availability='UNAVAILABLE';values.hidden=true;overflow.hidden=true;return; }
    root.dataset.av01Availability='READY';values.hidden=false;legend.hidden=false;legendDetails.hidden=false;displaySummary.hidden=false;retry.hidden=true;
    if (!viewTransform) { const size=svg.getBoundingClientRect();const displaced=layers.deformation&&view.deformation.available?displacedAnalysisNodes(view.nodes,view.deformation.alpha):null;viewTransform=fitAnalysisVisualization(displaced?[...view.nodes,...displaced]:view.nodes,size.width,size.height,VISUAL_CALIBRATION); }
    const rendered=renderAnalysisVisualization(svg,view,{layers,viewTransform,alpha:view.deformation.alpha,selected});
    for(const [key,button] of listButtons)button.setAttribute('aria-pressed',String(Boolean(selected&&objectKey(selected)===key)));
    overflow.hidden=!rendered.overflow;
    const descriptions=['坐标 mm；力 N。箭头长度经过显示缩放，请以数值为准。尺寸标注为保存的原始节点范围，不量测变形图。'];
    descriptions.push(rendered.deformationOn?'原始结构：浅灰虚线；变形结构：主线。':'原始结构：主线。');
    if(layers.forceStates&&view.forceStatesAvailable) descriptions.push('拉伸：红色实线；压缩：蓝色长虚线；近零力：灰色点线；混合状态：紫色点划线，按各分析段查看。');
    if(layers.reactions&&view.reactionsAvailable) descriptions.push('支座反力：绿色，由原始节点向外。');
    if(layers.loads&&view.loadsAvailable) descriptions.push(view.loads.length?'外部荷载：橙色，指向原始节点；逐笔显示。':'本次未保存外部荷载。');
    if(view.maximumCandidates.length) descriptions.push(`最大位移候选（圈标）：${view.maximumCandidates.map(id=>view.labels.analysisNode(id)).join('、')}。`);
    legend.textContent=descriptions.join(' ');
    displaySummary.textContent='坐标 mm；力 N。箭头长度经过显示缩放，请以数值为准。'+(layers.deformation&&view.deformation.available ? ` AUTO ×${formatVisualizationNumber(view.deformation.alpha)} · 最大位移 ${formatVisualizationNumber(view.deformation.maximumMm)} mm。` : '');
    status.textContent=!rendered.available && !rendered.hidden ? '这次分析的结构视图暂不可用，请查看已有数值资料。' : view.reactionsAvailable ? (view.reactions.length && view.reactions.every(row=>row.rx_N===0&&row.ry_N===0) ? '本次支座反力均为 0 N（无方向箭头）。' : '结构视图已载入。') : '支座反力暂不可用；仍可查看原始结构。';
    for(const row of view.nodes) {const tr=element('tr');tr.append(element('th',{scope:'row'},view.labels.analysisNode(row.analysis_node_id)),element('td',{},formatVisualizationNumber(row.displacement?.ux_mm,{exact:true})),element('td',{},formatVisualizationNumber(row.displacement?.uy_mm,{exact:true})));displacementBody.append(tr);}
    if(layers.deformation&&rendered.deformationOn){exactScale.hidden=false;exactScale.textContent=`显示倍率原值 ${String(rendered.alpha)}×；最大位移 ${formatVisualizationNumber(view.deformation.maximumMm,{exact:true})} mm。`;}
    for(const row of view.loads) {
      const tr=element('tr',{'data-av01-load-row':''});
      tr.append(element('th',{scope:'row'},`${view.labels.label('NODE_LOAD',row.load_id)} · ${view.labels.analysisNode(row.analysis_node_id)}`),
        element('td',{},formatVisualizationNumber(row.fx_N,{exact:true})),element('td',{},formatVisualizationNumber(row.fy_N,{exact:true})));loadBody.append(tr);
    }
    for (const row of view.reactions) {
      const tr=element('tr',{'data-av01-reaction-row':''});
      const supports=(row.support_ids||[]).map(id=>view.labels.label('SUPPORT',id)).join('、');
      tr.append(element('th',{scope:'row'}, `${view.labels.analysisNode(row.analysis_node_id)} · ${supports}`),
        element('td',{},formatVisualizationNumber(row.rx_N,{exact:true})),element('td',{},formatVisualizationNumber(row.ry_N,{exact:true})));body.append(tr);
    }
  };
  for(const [key,{input}] of controlRows) input.addEventListener('change',()=>{layers[key]=input.checked;draw();});
  const rebuild=()=>{view=projection?buildAnalysisVisualizationView({projection,expectedContext,teachingView}):null;if(selected&&!view?.objects?.has(objectKey(selected)))selected=null;syncObjects();draw();};
  const cancelPan=()=>{
    const active=drag;drag=null;
    if(frame!==null){cancelAnimationFrame(frame);frame=null;}
    if(active&&svg.hasPointerCapture(active.id))svg.releasePointerCapture(active.id);
  };
  const clear=()=>{cancelPan();cancelHover(true);selected=null;loadState=null;retry.hidden=true;projection=null;expectedContext=null;teachingView=null;view=null;viewTransform=null;syncObjects();draw();};
  fit.addEventListener('click',()=>{viewTransform=null;draw();});
  const zoom=(factor,anchor=null)=>{if(!viewTransform||!view?.available)return;const size=svg.getBoundingClientRect();const point=anchor||{x:size.width/2,y:size.height/2};
    const next={...viewTransform,scale:viewTransform.scale*factor,panX:point.x+(viewTransform.panX-point.x)*factor,panY:point.y+(viewTransform.panY-point.y)*factor};
    if([next.scale,next.panX,next.panY].every(finite)&&next.scale>0){viewTransform=next;draw();}};
  zoomIn.addEventListener('click',()=>zoom(1.2));zoomOut.addEventListener('click',()=>zoom(1/1.2));
  svg.addEventListener('wheel',event=>{if(!view?.available)return;event.preventDefault();const rect=svg.getBoundingClientRect();zoom(event.deltaY<0?1.1:1/1.1,{x:event.clientX-rect.left,y:event.clientY-rect.top});},{passive:false});
  svg.addEventListener('pointerdown',event=>{if(!viewTransform||!view?.available||![0,1].includes(event.button))return;event.preventDefault();cancelHover();svg.focus({preventScroll:true});drag={id:event.pointerId,x:event.clientX,y:event.clientY,transform:{...viewTransform},object:recordFor(event.target)?.record.ref};svg.setPointerCapture(event.pointerId);});
  svg.addEventListener('pointermove',event=>{if(!drag||event.pointerId!==drag.id)return;viewTransform={...drag.transform,panX:drag.transform.panX+event.clientX-drag.x,panY:drag.transform.panY+event.clientY-drag.y};if(frame===null)frame=requestAnimationFrame(()=>{frame=null;draw();});});
  const endPan=event=>{cancelHover();if(!drag||event.pointerId!==drag.id)return;const active=drag;if(event.type==='pointercancel')viewTransform=active.transform;drag=null;if(svg.hasPointerCapture(event.pointerId))svg.releasePointerCapture(event.pointerId);if(event.type==='pointerup'&&active.object&&Math.hypot(event.clientX-active.x,event.clientY-active.y)<3)selectObject(active.object);else draw();};
  svg.addEventListener('pointerup',endPan);svg.addEventListener('pointercancel',endPan);

  const previewMove=event=>{
    if(drag||event.pointerType==='touch'||!isVisible()){cancelHover();return;}
    const target=recordFor(event.target);
    if(!target){cancelHover(true);return;}
    if(dismissedHover===target.key)return;
    if(dismissedHover!==target.key)dismissedHover=null;
    cancelHover();const generation=hoverGeneration,epoch=selection?.epoch,runId=selection?.runId;
    hoverTarget=target;hoverAnchor={x:event.clientX,y:event.clientY};
    pendingHover=setTimeout(()=>{
      pendingHover=null;
      if(destroyed||generation!==hoverGeneration||selection?.epoch!==epoch||selection?.runId!==runId||!isVisible()
        ||!target.hit.isConnected||!svg.contains(target.hit)||view?.objects?.get(target.key)!==target.record)return;
      tooltip.replaceChildren(element('strong',{},target.record.name));rowsInto(tooltip,target.record.preview,{preview:true});tooltip.hidden=false;
      const frame=wrap.getBoundingClientRect(),canvas=svg.getBoundingClientRect(),box=tooltip.getBoundingClientRect();
      const left=Math.max(canvas.left,0),right=Math.min(canvas.right,innerWidth),top=Math.max(canvas.top,0),bottom=Math.min(canvas.bottom,innerHeight);
      if(right-left<box.width||bottom-top<box.height){cancelHover();return;}
      let x=hoverAnchor.x+16,y=hoverAnchor.y+20;if(x+box.width>right-4)x=hoverAnchor.x-box.width-16;if(y+box.height>bottom-4)y=hoverAnchor.y-box.height-16;
      tooltip.style.left=`${Math.max(left+4,Math.min(x,right-box.width-4))-frame.left}px`;
      tooltip.style.top=`${Math.max(top+4,Math.min(y,bottom-box.height-4))-frame.top}px`;
    },VISUAL_CALIBRATION.hoverDelayMs);
  };
  svg.addEventListener('pointermove',previewMove);svg.addEventListener('pointerleave',()=>cancelHover(true));
  const escape=event=>{if(event.key==='Escape'&&!event.isComposing)dismissHover();};root.addEventListener('keydown',escape);
  const hidden=()=>{if(!isVisible()){cancelHover();cancelPan();}};document.addEventListener('visibilitychange',hidden);
  const mutations=new MutationObserver(()=>{hidden();if(hoverTarget&&!hoverTarget.hit.isConnected)cancelHover();});
  mutations.observe(svg,{childList:true,subtree:true});for(let parent=root;parent;parent=parent.parentElement)mutations.observe(parent,{attributes:true,attributeFilter:['hidden','style','class','data-ux-stage','data-ux-results-view']});
  let lastSize=null,wasHidden=false;
  const observer=new ResizeObserver(()=>{const size=svg.getBoundingClientRect();const next=`${size.width}:${size.height}`;if(size.width<=0||size.height<=0){wasHidden=true;hidden();return;}if(next!==lastSize){if(lastSize!==null)viewTransform=null;lastSize=next;wasHidden=false;draw();}else if(wasHidden){wasHidden=false;draw();}});observer.observe(svg);
  clear();
  return Object.freeze({
    setSelection(value){if(destroyed)return;selection={...value};layers={...DEFAULT_LAYERS};clear();},
    useProjection(event){if(destroyed||!selection||event.runId!==selection.runId||event.epoch!==selection.epoch)return;
      if(event.kind!=='READY'){clear();loadState=event.kind;draw();return;}
      if(event.expectedContext?.runId!==selection.runId){clear();loadState='UNAVAILABLE';draw();return;}
      loadState='READY';projection=structuredClone(event.projection);expectedContext=structuredClone(event.expectedContext);rebuild();},
    useTeachingView(value,epoch){if(destroyed||!selection||epoch!==selection.epoch)return;teachingView=value;rebuild();},
    // Resolve only the already-projected Saved Run mapping; select an existing segment.
    focusPhysicalMember(id){
      const segment=view?.segments.find(row=>row.physical_member_id===id);
      if(!segment)return false;
      selectObject({kind:'ANALYSIS_SEGMENT',id:segment.analysis_segment_id});return true;
    },
    clear,
    dismissHover,
    setVisible(value){visible=Boolean(value);if(!visible){cancelHover();cancelPan();}else draw();},
    destroy(){if(destroyed)return;destroyed=true;cancelPan();cancelHover(true);observer.disconnect();mutations.disconnect();document.removeEventListener('visibilitychange',hidden);root.removeEventListener('keydown',escape);root.replaceChildren();}
  });
}
