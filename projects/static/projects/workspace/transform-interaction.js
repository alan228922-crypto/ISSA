import { captureMemberGroup } from './transform-geometry.js';
import { memberParticipationByNode } from './draft-topology.js';
import { resolvePointerPoint } from './geometry.js';
import { readCoordinateSpace } from './coordinate-space.js';
import { getSnapCandidateIndex, querySnapCandidates } from './snap-candidates.js';
import { parseCadInput } from './cad-input.js';
import { applyWorkspaceEditorAction } from './state.js';

export function bindTransformTools({ root, svg, canvasController, materials, sections, readOnly }) {
  const toolbar = root.querySelector('[data-cad-transform-toolbar]');
  if (!toolbar || readOnly || canvasController.getState().draft.schema_version !== 'physical-draft-v2') { if (toolbar) toolbar.hidden = true; return; }
  const panel = root.querySelector('[data-transform-panel]'), status = root.querySelector('[data-transform-status]');
  const applyButton = panel.querySelector('[data-transform-apply]'), previewButton = panel.querySelector('[data-transform-preview-button]');
  const dx = panel.querySelector('[data-transform-dx]'), dy = panel.querySelector('[data-transform-dy]'), ack = panel.querySelector('[data-transform-ack]');
  const angle = panel.querySelector('[data-transform-angle]');
  const commandInput = root.querySelector('[data-cad-transform-command]');
  const resources = { materialIds: materials.map(row => row.id), sectionIds: sections.map(row => row.id) };
  let clipboard = null, pasteIndex = 0, session = null, dragStart = null, composing = false;
  const copying = kind => kind === 'COPY' || kind === 'PASTE';
  const memberKeys = () => (canvasController.getState().selectedObjects || []).filter(row => row.kind === 'PHYSICAL_MEMBER').map(row => row.clientKey);
  const signature = () => (canvasController.getState().selectedObjects || []).map(row => `${row.kind}:${row.clientKey}`).sort().join('\n');
  const editing = () => !canvasController.getState().readOnly && root.dataset.uxStage === 'build' && canvasController.getState().cad?.activeCommand === 'SELECT';
  const tell = text => { if (status.textContent !== text) status.textContent = text; };
  const error = e => tell(({ TRANSFORM_SELECTION_REQUIRED: '请先选择完整的杆件。', TRANSFORM_INCOMPLETE_GROUP: '所选杆件不完整，请先补齐端点、材料和截面。', TRANSFORM_RESOURCE_UNAVAILABLE: '复制内容的材料或截面已不可用，请重新选择。', TRANSFORM_INVALID_VALUE: '请输入完整、有限的数值。', TRANSFORM_SHARED_NODE: '所选群组连接了未选取的相邻杆件，请一并选择相关相邻杆件。' })[e.code] || '目标位置会产生重合或不合法的连接，原模型未改变。');
  const removeGhost = () => svg.querySelector('[data-transform-preview]')?.remove();
  const cancel = (text = '') => { session = null; dragStart = null; panel.hidden = true; applyButton.disabled = true; commandInput.value = ''; removeGhost(); if (text) tell(text); };
  const ghost = draft => {
    removeGhost(); const layer = svg.querySelector('[data-world-layer]'); if (!layer || !session) return;
    const g = document.createElementNS(svg.namespaceURI, 'g'); g.dataset.transformPreview = ''; g.setAttribute('pointer-events', 'none'); g.setAttribute('aria-hidden', 'true');
    const nodes = new Map(draft.nodes.map(row => [row.client_key, row]));
    for (const row of draft.physical_members.filter(row => session.previewKeys.includes(row.client_key))) {
      const a = nodes.get(row.start_node_client_key), b = nodes.get(row.end_node_client_key);
      const line = document.createElementNS(svg.namespaceURI, 'line');
      for (const [key, value] of Object.entries({ x1: a.x_mm, y1: a.y_mm, x2: b.x_mm, y2: b.y_mm, stroke: '#7c3aed', 'stroke-width': 3, 'stroke-dasharray': '6 4', 'vector-effect': 'non-scaling-stroke' })) line.setAttribute(key, value);
      g.append(line);
    }
    if (session.nodeKey) { const n = nodes.get(session.nodeKey); const dot = document.createElementNS(svg.namespaceURI, 'circle'); for (const [key,value] of Object.entries({cx:n.x_mm,cy:n.y_mm,r:4,fill:'#7c3aed'})) dot.setAttribute(key,value); g.append(dot); }
    layer.append(g);
  };
  const number = input => { if (!input.value.trim() || !Number.isFinite(Number(input.value))) { const e = new Error(); e.code = 'TRANSFORM_INVALID_VALUE'; throw e; } return Number(input.value); };
  const invalidatePreview = () => { if (session) { session.invalidPreview = true; session.previewDraft = null; } applyButton.disabled = true; removeGhost(); };
  const preview = () => {
    if (!session || !session.action || session.invalidPreview) return false;
    try {
      const current = canvasController.getState();
      if (current.draft !== session.basis || signature() !== session.selection) { cancel('模型或选择已改变，请重新开始操作。'); return false; }
      if (session.kind === 'MOVE') session.action.transform = { kind: 'TRANSLATE', dx: number(dx), dy: number(dy) };
      if (session.kind === 'ROTATE') session.action.transform = { kind: 'ROTATE', angle: number(angle), ...(session.center ? { center: session.center } : {}) };
      const planned = applyWorkspaceEditorAction(current, session.action);
      session.previewDraft = planned.draft;
      const oldKeys = new Set(current.draft.physical_members.map(row => row.client_key));
      session.previewKeys = copying(session.kind) ? planned.draft.physical_members.filter(row => !oldKeys.has(row.client_key)).map(row => row.client_key) : ['STRETCH','LENGTH'].includes(session.kind) ? [...(memberParticipationByNode(current.draft).get(session.nodeKey) || [])] : session.action.memberKeys || session.memberKeys;
      applyButton.disabled = planned === current; ghost(planned.draft); return !applyButton.disabled;
    } catch (e) { session.previewDraft = null; applyButton.disabled = true; removeGhost(); error(e); return false; }
  };
  const preparePanel = kind => {
    panel.hidden = false; panel.querySelector('[data-transform-translate]').hidden = kind !== 'MOVE'; panel.querySelector('[data-transform-rotate]').hidden = kind !== 'ROTATE'; previewButton.hidden = kind === 'PASTE'; ack.checked = false;
    panel.querySelector('[data-transform-ack-label]').hidden = true; panel.querySelector('[data-transform-attachments]').textContent = '';
  };
  const paste = () => {
    if (!editing() || !clipboard) return;
    cancel(); const basis = canvasController.getState().draft;
    session = { kind: 'PASTE', basis, selection: signature(), action: { type: 'PASTE_MEMBER_GROUP', group: clipboard, offset: { x: 20 * (pasteIndex + 1), y: 20 * (pasteIndex + 1) }, resources }, previewKeys: [], attachments: 0 };
    preparePanel('PASTE'); panel.querySelector('[data-transform-title]').textContent = `粘贴预览：ΔX = ${20 * (pasteIndex + 1)} mm，ΔY = ${20 * (pasteIndex + 1)} mm`;
    tell('复制杆件及节点，不包含支座和荷载。确认预览后应用。'); preview();
  };
  const copy = (interactive = false) => {
    if (!editing()) return;
    try { clipboard = captureMemberGroup(canvasController.getState().draft, memberKeys()); pasteIndex = 0; cancel(); tell('复制杆件及节点，不包含支座和荷载。'); sync(); if (interactive) beginCopy(); } catch (e) { error(e); }
  };
  const beginCopy = () => {
    cancel(); const basis = canvasController.getState().draft;
    session = { kind: 'COPY', phase: 'BASE', basis, selection: signature(), action: { type: 'PASTE_MEMBER_GROUP', group: clipboard, offset: { x: 0, y: 0 }, resources }, previewKeys: [], attachments: 0 };
    preparePanel('COPY'); applyButton.disabled = true; panel.querySelector('[data-transform-title]').textContent = '复制：指定基点，再指定放置点'; tell('请选择基点。复制杆件及节点，不包含支座和荷载。'); svg.focus({ preventScroll: true });
  };
  const openTransform = kind => {
    if (!editing()) return;
    cancel();
    try {
      const current = canvasController.getState(), keys = memberKeys(), group = captureMemberGroup(current.draft, keys);
      const action = { type: 'TRANSFORM_MEMBER_GROUP', memberKeys: keys, transform: kind === 'MOVE' ? { kind: 'TRANSLATE', dx: 0, dy: 0 } : { kind: 'ROTATE', angle: 0 } };
      applyWorkspaceEditorAction(current, action); // Existing v2 atomic preflight, including shared-node boundary.
      const nodeKeys = new Set(group.nodes.map(row => row.client_key));
      const supports = current.draft.supports.filter(row => nodeKeys.has(row.target_node_client_key)).length;
      const loads = current.draft.node_loads.filter(row => nodeKeys.has(row.target_node_client_key)).length;
      session = { kind, phase: kind === 'MOVE' ? 'BASE' : 'CENTER', basis: current.draft, selection: signature(), action, previewKeys: keys, attachments: supports + loads };
      preparePanel(kind); dx.value = '0'; dy.value = '0'; angle.value = '0'; panel.querySelector('[data-transform-title]').textContent = kind === 'MOVE' ? '移动杆件组' : '旋转杆件组（唯一端点中心，逆时针为正）';
      panel.querySelector('[data-transform-attachments]').textContent = `支座 ${supports}，荷载 ${loads}。附件随节点移动，保持原全局方向、分量和引用。`;
      panel.querySelector('[data-transform-ack-label]').hidden = !session.attachments;
      svg.focus({ preventScroll: true });
      tell(kind === 'MOVE' ? '请选择基点和目标点；也可拖动已选杆件，松开应用；或输入 ΔX / ΔY 后预览、应用。' : '请选择旋转中心；或直接输入角度（°）使用群组中心；支座方向和荷载分量保持全局定义。'); preview();
    } catch (e) { error(e); }
  };
  const chooseNode = key => {
    const draft = canvasController.getState().draft, node = draft.nodes.find(row => row.client_key === key);
    const endpoints = draft.physical_members.filter(row => session.memberKeys.includes(row.client_key)).flatMap(row => [row.start_node_client_key,row.end_node_client_key]);
    if (!node || (endpoints.length && !endpoints.includes(key))) { tell('请选择所选杆件的端点。'); return; }
    session.nodeKey = key; session.base = {x:node.x_mm,y:node.y_mm}; session.phase = session.kind === 'STRETCH' ? 'TARGET' : 'VALUE';
    session.previewKeys = [...(memberParticipationByNode(draft).get(key) || [])];
    const supports = draft.supports.filter(row => row.target_node_client_key === key).length, loads = draft.node_loads.filter(row => row.target_node_client_key === key).length;
    panel.querySelector('[data-transform-attachments]').textContent = `支座 ${supports}，荷载 ${loads}；随节点移动，保持全局方向、分量和引用。相连杆件将同步变形。`;
    tell(session.kind === 'STRETCH' ? '指定目标点，或直接输入绝对坐标 X,Y。' : '输入总长度（mm），或 +40 / -20 增减量；Enter 应用。');
  };
  const openNodeEdit = (kind, nodeKey = null) => {
    if (!editing()) return;
    cancel(); const current = canvasController.getState(), keys = memberKeys();
    if (kind === 'LENGTH' && keys.length !== 1) { tell('修改长度需要只选择一根完整杆件。'); return; }
    if (!keys.length && !nodeKey) nodeKey = current.selectedObjects.find(row => row.kind === 'GEOMETRY_NODE')?.clientKey;
    if (!keys.length && !nodeKey) { tell('请先选择杆件或节点。'); return; }
    session = { kind, phase:'NODE', basis:current.draft, selection:signature(), memberKeys:keys, previewKeys:[], action:null, attachments:0 };
    preparePanel(kind); applyButton.disabled = true; panel.querySelector('[data-transform-title]').textContent = kind === 'STRETCH' ? '拉伸：移动节点，保留连接' : '修改长度：选择移动端点';
    tell('请选择要移动的端点。'); if (nodeKey) chooseNode(nodeKey); svg.focus({preventScroll:true});
  };
  const apply = () => {
    if (!session || !editing() || !preview()) return;
    if (session.attachments && !ack.checked) { tell('请先确认附件随节点移动，方向和数值保持不变。'); return; }
    try {
      const current = canvasController.getState(), next = applyWorkspaceEditorAction(current, session.action), kind = session.kind;
      const repeat = kind === 'COPY' ? { group: session.action.group, base: session.base } : null;
      const selectedObjects = ['STRETCH','LENGTH'].includes(kind) ? current.selectedObjects : session.previewKeys.map(clientKey => ({ kind: 'PHYSICAL_MEMBER', clientKey }));
      cancel(); if (kind === 'PASTE') pasteIndex++;
      canvasController.replaceState({ ...next, selectedObjects, selectedObject: selectedObjects.at(-1) || null, focusedObject: null });
      root.querySelector('#workspace-save-status').textContent = next.dirty ? '未保存修改：有' : '未保存修改：无';
      if (repeat) {
        session = { kind: 'COPY', phase: 'TARGET', base: repeat.base, basis: next.draft, selection: signature(), action: { type: 'PASTE_MEMBER_GROUP', group: repeat.group, offset: {x:0,y:0}, resources }, previewKeys: [], attachments: 0 };
        preparePanel('COPY'); applyButton.disabled = true; tell('复制完成。继续指定放置点；Esc 或结束命令退出。不包含支座和荷载。');
      } else tell(kind === 'PASTE' ? '粘贴完成；新杆件已选中。' : kind === 'MOVE' ? '移动完成；杆件与节点标识保持不变。' : kind === 'ROTATE' ? '旋转完成；杆件与节点标识保持不变。' : '节点已更新；标识、连接与附件引用保持不变。'); svg.focus({ preventScroll: true });
    } catch (e) { error(e); }
  };
  const inputValue = () => {
    if (!session) return false;
    invalidatePreview();
    const text = commandInput.value.trim();
    if (session.kind === 'MOVE' || session.kind === 'COPY') {
      const parsed = parseCadInput(text, null);
      if (!parsed.ok || parsed.kind !== 'ABSOLUTE') return false;
      if (session.kind === 'COPY') { if (!session.base) return false; session.action.offset = {x:parsed.point.x,y:parsed.point.y}; }
      else { dx.value = String(parsed.point.x); dy.value = String(parsed.point.y); }
    } else if (session.kind === 'ROTATE') {
      if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(text) || !Number.isFinite(Number(text))) return false;
      angle.value = text;
    } else if (session.kind === 'STRETCH') {
      const parsed = parseCadInput(text, null); if (!session.nodeKey || !parsed.ok || parsed.kind !== 'ABSOLUTE') return false;
      session.action = {type:'UPDATE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:session.nodeKey},changes:{x_mm:parsed.point.x,y_mm:parsed.point.y}};
    } else if (session.kind === 'LENGTH') {
      if (!session.nodeKey || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(text) || !Number.isFinite(Number(text))) return false;
      session.action = {type:'RESIZE_MEMBER',memberKey:session.memberKeys[0],nodeKey:session.nodeKey,mode:/^[+-]/.test(text)?'DELTA':'TOTAL',value:Number(text)};
    } else return false;
    session.invalidPreview = false;
    return preview();
  };
  commandInput.addEventListener('input', () => { if (session && !inputValue()) { applyButton.disabled = true; removeGhost(); } });
  commandInput.addEventListener('keydown', event => {
    if (event.key !== 'Enter' || event.isComposing || composing || event.keyCode === 229 || event.repeat) return;
    event.preventDefault(); event.stopPropagation();
    const verb = commandInput.value.trim().toUpperCase();
    if (!session && ['CO', 'M', 'RO', 'ST', 'LEN'].includes(verb)) {
      if (verb === 'ST' || verb === 'LEN') openNodeEdit(verb === 'ST' ? 'STRETCH' : 'LENGTH'); else if (verb === 'CO') copy(true); else openTransform(verb === 'M' ? 'MOVE' : 'ROTATE'); commandInput.value = ''; svg.focus({ preventScroll: true });
    } else if (session && inputValue()) apply();
    else tell('命令或数值无效，请输入 M / RO、位移 ΔX,ΔY 或角度。');
  });
  const sync = () => {
    const active = editing(); toolbar.hidden = root.dataset.uxStage !== 'build';
    toolbar.querySelector('[data-cad-copy]').disabled = !active || !memberKeys().length;
    toolbar.querySelector('[data-cad-paste]').disabled = !active || !clipboard;
    toolbar.querySelector('[data-cad-move]').disabled = !active || !memberKeys().length;
    toolbar.querySelector('[data-cad-rotate]').disabled = !active || !memberKeys().length;
    toolbar.querySelector('[data-cad-stretch]').disabled = !active || !(memberKeys().length || canvasController.getState().selectedObjects.some(row => row.kind === 'GEOMETRY_NODE'));
    toolbar.querySelector('[data-cad-length]').disabled = !active || memberKeys().length !== 1;
  };
  toolbar.querySelector('[data-cad-copy]').addEventListener('click', () => copy(true));
  toolbar.querySelector('[data-cad-paste]').addEventListener('click', paste);
  toolbar.querySelector('[data-cad-move]').addEventListener('click', () => openTransform('MOVE'));
  toolbar.querySelector('[data-cad-rotate]').addEventListener('click', () => openTransform('ROTATE'));
  toolbar.querySelector('[data-cad-stretch]').addEventListener('click', () => openNodeEdit('STRETCH'));
  toolbar.querySelector('[data-cad-length]').addEventListener('click', () => openNodeEdit('LENGTH'));
  toolbar.querySelector('[data-cad-clear-selection]').addEventListener('click', () => { cancel(); const current = canvasController.getState(); canvasController.replaceState({ ...current, selectedObjects: [], selectedObject: null, focusedObject: null }); svg.focus({ preventScroll: true }); });
  panel.querySelector('[data-transform-cancel]').addEventListener('click', () => { cancel('已取消，模型未改变。'); svg.focus({ preventScroll: true }); });
  applyButton.addEventListener('click', apply); previewButton.addEventListener('click', preview);
  for (const field of [dx, dy, angle]) field.addEventListener('input', () => { commandInput.value = ''; if (session) session.invalidPreview = false; preview(); });
  root.addEventListener('compositionstart', () => { composing = true; });
  root.addEventListener('compositionend', () => { composing = false; });
  root.addEventListener('focusout', () => { composing = false; });
  root.addEventListener('keydown', event => {
    if (event.key === 'Escape' && (composing || event.isComposing || event.keyCode === 229)) { event.stopPropagation(); return; }
    if (event.key === 'Escape' && (session || commandInput.value || event.target === commandInput)) { event.preventDefault(); event.stopPropagation(); cancel('已取消，模型未改变。'); svg.focus({ preventScroll: true }); return; }
    const canvasFocus = event.target === svg || svg.contains(event.target);
    if (event.key === 'Enter' && session && editing() && canvasFocus && !event.defaultPrevented && !composing && !event.isComposing && event.keyCode !== 229 && !event.repeat && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey) { event.preventDefault(); event.stopPropagation(); if (!applyButton.disabled) apply(); return; }
    if (!event.defaultPrevented && editing() && canvasFocus && !composing && !event.isComposing && event.keyCode !== 229 && !event.repeat && !event.ctrlKey && !event.metaKey && !event.altKey && (session ? /^[0-9+.\-]$/.test(event.key) : /^[a-z]$/i.test(event.key))) {
      event.preventDefault(); commandInput.value = event.key; commandInput.focus({ preventScroll: true }); commandInput.dispatchEvent(new Event('input', { bubbles: true })); return;
    }
    if (event.defaultPrevented || !editing() || composing || event.isComposing || event.keyCode === 229 || event.repeat || event.altKey || event.shiftKey || !(event.ctrlKey || event.metaKey) || !(event.target === svg || svg.contains(event.target))) return;
    if (event.key.toLowerCase() === 'c' && memberKeys().length) { event.preventDefault(); copy(); }
    if (event.key.toLowerCase() === 'v' && clipboard) { event.preventDefault(); paste(); }
  }, true);
  const resolvePoint = (world, screen) => {
    const state = canvasController.getState(), cad = state.cad, coordinates = readCoordinateSpace(svg, state.viewTransform);
    const candidates = cad.objectSnap === false ? [] : querySnapCandidates(getSnapCandidateIndex(state.draft), { clientPoint: screen, coordinates }).filter(row => row.nodeClientKey !== session?.nodeKey);
    return resolvePointerPoint({ worldPointer: world, clientPointer: screen, coordinates, candidates, origin: session?.base || null, ortho: session?.kind !== 'ROTATE' && (cad.ortho || cad.temporaryOrtho), gridEnabled: cad.gridSnap, explicitNumeric: false }).worldPoint;
  };
  const pointPreview = (world, screen) => {
    if (!session || !world || session.phase !== 'TARGET' || root.querySelector('input:focus,textarea:focus,select:focus')) return false;
    try {
      const p = resolvePoint(world, screen); session.invalidPreview = false;
      if (session.kind === 'MOVE') { dx.value = String(p.x-session.base.x); dy.value = String(p.y-session.base.y); }
      if (session.kind === 'COPY') session.action.offset = { x: p.x-session.base.x, y: p.y-session.base.y };
      if (session.kind === 'STRETCH') session.action = {type:'UPDATE_OBJECT',target:{kind:'GEOMETRY_NODE',clientKey:session.nodeKey},changes:{x_mm:p.x,y_mm:p.y}};
      if (session.kind === 'ROTATE') angle.value = String(Math.atan2(p.y-session.center.y,p.x-session.center.x)*180/Math.PI);
      return preview();
    } catch (e) { invalidatePreview(); error(e); return false; }
  };
  canvasController.setCommandHandlers({
    active: () => Boolean(session && session.kind !== 'PASTE' && editing()),
    onMove: pointPreview,
    onPoint: (world, target, screen) => {
      if (!session || !world) return;
      commandInput.value = ''; svg.focus({ preventScroll: true });
      try {
        if (session.phase === 'NODE') { if (target?.kind === 'GEOMETRY_NODE') chooseNode(target.clientKey); else tell('请选择要移动的端点。'); return; }
        if (session.phase === 'VALUE') { tell('请输入长度或增减量并按 Enter。'); return; }
        if (session.phase === 'BASE' || session.phase === 'CENTER') {
          const p = resolvePoint(world, screen);
          if (session.phase === 'CENTER') session.center = p; else session.base = p;
          session.phase = 'TARGET'; tell(session.kind === 'ROTATE' ? '指定方向预览角度，或直接输入角度并按 Enter。' : '指定目标点，或直接输入相对位移 ΔX,ΔY 并按 Enter。'); return;
        }
        if (pointPreview(world, screen)) apply();
      } catch (e) { invalidatePreview(); error(e); }
    },
  });
  svg.addEventListener('cad-coordinate-error', () => cancel('坐标暂不可用，命令已取消。'));
  svg.addEventListener('cad-gesture-cancel', () => { if (session) cancel('已取消，模型未改变。'); });
  const dragPreview = point => {
    if (!session || session.kind !== 'MOVE' || !dragStart || !point) return false;
    const x = point.x-dragStart.x, y = point.y-dragStart.y;
    if (!Number.isFinite(x) || !Number.isFinite(y)) { invalidatePreview(); return false; }
    session.invalidPreview = false; commandInput.value = ''; dx.value = String(x); dy.value = String(y); return preview();
  };
  canvasController.setTransformDragHandlers({
    onStart: (target, point) => { if (!editing() || session?.kind !== 'MOVE' || target?.kind !== 'PHYSICAL_MEMBER' || !session.action.memberKeys.includes(target.clientKey) || !point) return false; dragStart = point; return true; },
    onPreview: dragPreview,
    onCommit: point => { if (dragPreview(point)) apply(); dragStart = null; },
    onCancel: () => cancel('已取消，模型未改变。'),
  });
  window.addEventListener('blur', () => { composing = false; cancel(); });
  canvasController.subscribeStateChange(state => { if (session && (state.draft !== session.basis || signature() !== session.selection || !editing())) cancel(); sync(); if (session?.previewDraft) ghost(session.previewDraft); });
  new MutationObserver(() => { if (!editing()) cancel(); sync(); }).observe(root, { attributes: true, attributeFilter: ['data-ux-stage'] });
  sync();
  return Object.freeze({
    available: () => !canvasController.getState().readOnly && root.dataset.uxStage === 'build',
    active: () => Boolean(session || canvasController.getState().cad?.activeCommand !== 'SELECT'),
    canApply: () => Boolean(session && !applyButton.disabled && (!session.attachments || ack.checked)),
    confirm: apply,
    finish: () => { if (!session) root.querySelector('[data-workspace-tool="SELECT"]').click(); cancel('命令已结束；未应用的预览已取消。'); svg.focus({preventScroll:true}); },
    cancel: () => { if (!session) root.querySelector('[data-workspace-tool="SELECT"]').click(); cancel('已取消，模型未改变。'); svg.focus({preventScroll:true}); },
    paste,
    hasClipboard: () => Boolean(clipboard),
    start: (code, nodeKey = null) => {
      if (code === 'CO') copy(true);
      else if (code === 'M' || code === 'RO') openTransform(code === 'M' ? 'MOVE' : 'ROTATE');
      else if (code === 'ST' || code === 'LEN') openNodeEdit(code === 'ST' ? 'STRETCH' : 'LENGTH', nodeKey);
    },
  });
}
