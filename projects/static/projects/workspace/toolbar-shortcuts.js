const AIDS = Object.freeze([
  ['grid-visible', 'F7', 'GRID'], ['snap', 'F9', 'GSNAP'],
  ['object-snap', 'F3', 'OSNAP'], ['ortho', 'F8', 'ORTHO'],
  ['tracking', 'F11', 'TRACK'], ['dynamic-input', 'F12', 'DYN'],
]);
const TOOLTIPS = Object.freeze([
  ['[data-cad-grid-visible]', '网格', '显示或隐藏画布网格，不改变几何。', 'F7 / GRID'],
  ['[data-cad-snap]', '网格吸附', '指针定位吸附到现有 1 mm 网格。', 'F9 / GSNAP'],
  ['[data-cad-object-snap]', '物件捕捉', '捕捉节点或构件交点；交叉不自动连接。', 'F3 / OSNAP'],
  ['[data-cad-ortho]', '正交', '限制指针方向为水平或竖直。', 'F8 / ORTHO'],
  ['[data-cad-tracking]', '追踪', '沿已取得的捕捉位置显示追踪辅助。', 'F11 / TRACK'],
  ['[data-cad-dynamic-input]', '动态输入', '切换随指针显示的动态数值；直接键盘输入仍可用。', 'F12 / DYN'],
  ['[data-cad-undo]', '撤销', '撤销上一笔已提交的模型编辑。', 'Ctrl/Cmd+Z'],
  ['[data-cad-redo]', '重做', '恢复刚撤销的模型编辑。', 'Ctrl+Y / Cmd+Shift+Z'],
  ['#workspace-save', '保存模型', '保存已提交的模型，不应用未完成的预览。', 'Ctrl/Cmd+S'],
  ['[data-cad-copy]', '复制', '选择杆件，指定基点和放置点，可连续复制；不复制支座与荷载。', 'CO → Enter'],
  ['[data-cad-paste]', '粘贴', '粘贴应用内杆件副本，默认每次偏移 20 mm。', 'Ctrl/Cmd+V（画布）'],
  ['[data-cad-move]', '平移', '选择杆件组，指定基点与目标点，或直接输入相对位移。', 'M → Enter'],
  ['[data-cad-rotate]', '旋转', '指定中心并输入角度；直接输入则使用群组端点中心。', 'RO → Enter'],
  ['[data-cad-stretch]', '拉伸', '移动既有节点；所有相连杆件跟随同一节点。', 'ST → Enter'],
  ['[data-cad-length]', '修改长度', '选择一根杆件的移动端点，输入总长或带符号增减量。', 'LEN → Enter'],
  ['[data-workspace-tool="SELECT"]', '选择', '点击或拖框选择对象，Shift 可追加选择。', '工具按钮'],
  ['[data-workspace-tool="NODE"]', '节点', '启用节点工具后，直接输入绝对坐标 X,Y。', 'Enter 确认 / Esc 取消'],
  ['[data-workspace-tool="MEMBER"]', '构件', '指定起点与终点，或起点后直接输入长度、Tab、角度。', 'Enter 确认 / Esc 取消'],
  ['[data-workspace-tool="SUPPORT"]', '支座', '启用支座工具，选择类型后点击节点。', '工具按钮'],
  ['[data-workspace-tool="LOAD"]', '荷载', '启用荷载工具，点击节点后编辑荷载分量。', '工具按钮'],
  ['[data-cad-shortcuts-open]', '快捷键说明', '查看命令、绘图辅助和保存操作说明。', '?（画布空闲时）'],
]);

function bindGuidance(root, svg) {
  const tooltip = document.createElement('div');
  tooltip.dataset.cadToolbarTooltip = ''; tooltip.id = 'cad-toolbar-tooltip'; tooltip.setAttribute('role', 'tooltip'); tooltip.hidden = true;
  document.body.append(tooltip);
  let anchor = null, description = null, activeRow = null;
  const hide = () => {
    tooltip.hidden = true;
    if (anchor) { if (description === null) anchor.removeAttribute('aria-describedby'); else anchor.setAttribute('aria-describedby', description); }
    anchor = null; activeRow = null;
  };
  const update = () => {
    if (!anchor || !activeRow) return;
    const selected = anchor.matches('[data-workspace-tool]'), pressed = anchor.getAttribute('aria-pressed');
    tooltip.textContent = `${activeRow[1]}\n${activeRow[2]}\n快捷键：${activeRow[3]}` + (pressed === null ? '' : `\n当前：${selected ? pressed === 'true' ? '已选择' : '未选择' : pressed === 'true' ? '开启' : '关闭'}`) + (anchor.disabled ? '\n当前不可用' : '');
    const a = anchor.getBoundingClientRect(), b = tooltip.getBoundingClientRect();
    tooltip.style.left = `${Math.max(8, Math.min(a.left, innerWidth - b.width - 8))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(a.top - b.height - 8, innerHeight - b.height - 8))}px`;
  };
  for (const row of TOOLTIPS) for (const button of root.querySelectorAll(row[0])) {
    const show = () => { hide(); anchor = button; description = button.getAttribute('aria-describedby'); activeRow = row; button.setAttribute('aria-describedby', [description, tooltip.id].filter(Boolean).join(' ')); tooltip.hidden = false; update(); };
    button.addEventListener('pointerenter', show); button.addEventListener('focus', show);
    button.addEventListener('pointerleave', hide); button.addEventListener('blur', hide);
    new MutationObserver(update).observe(button, { attributes: true, attributeFilter: ['aria-pressed', 'disabled'] });
  }
  const dialog = document.createElement('dialog'); dialog.dataset.cadShortcutsDialog = ''; dialog.setAttribute('aria-labelledby', 'cad-shortcuts-title');
  dialog.innerHTML = `<header><h2 id="cad-shortcuts-title">快捷键说明</h2><button type="button" data-close>关闭</button></header>
    <p>仅在可编辑建模区使用。文字编辑和输入法组字优先。Mac 可能需要 Fn；浏览器或系统可能保留 F11/F12，请使用按钮或文字命令备援。</p>
    <section><h3>建模命令</h3><p>节点：点击工具后直接输入 X,Y → Enter（绝对坐标）。构件：点击工具并指定起点，再输入长度 → Tab → 角度 → Enter。高级坐标格式保留在精确绘制区。</p></section>
    <section><h3>几何编辑</h3><p>选择杆件后输入 CO（复制）、M（平移）、RO（旋转）、ST（拉伸）、LEN（修改长度），再按 Enter。指定基点／中心／端点后可直接输入数值，无须点击输入框。</p><p>M：ΔX,ΔY；RO：角度（°），未指定中心时使用唯一端点中心；ST：绝对 X,Y；LEN：总长或 +40 / -20。CO 指定基点后连续放置。共享节点与非法几何仍受现有验证约束。</p></section>
    <section><h3>绘图辅助</h3><p>F7 网格 / GRID；F9 网格吸附 / GSNAP；F3 物件捕捉 / OSNAP；F8 正交 / ORTHO；F11 追踪 / TRACK；F12 动态输入 / DYN。</p><p>文字备援：选择工具处于空闲时，在画布直接键入命令并 Enter；当前几何命令中不会解释为辅助命令。交叉不自动连接。</p></section>
    <section><h3>撤销／保存</h3><p>Ctrl/Cmd+Z 撤销；Ctrl+Y / Cmd+Shift+Z 重做；Ctrl/Cmd+S 保存已提交模型，未完成的命令预览不会保存。Ctrl/Cmd+C / V 在画布使用应用内杆件剪贴簿；Copy 不包含支座／荷载。</p></section>
    <section><h3>取消／确认</h3><p>Enter 确认当前合法输入；Esc 按原命令规则取消。? 在画布空闲时打开本说明；Esc 关闭说明并返回原焦点。右键菜单提供当前可用操作。</p></section>`;
  document.body.append(dialog);
  let opener = null;
  const close = () => { dialog.close(); if (opener?.isConnected) opener.focus({ preventScroll: true }); };
  dialog.querySelector('[data-close]').addEventListener('click', close);
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  dialog.addEventListener('keydown', event => { if (event.key === 'Escape' && !event.isComposing && event.keyCode !== 229) { event.preventDefault(); event.stopPropagation(); close(); } });
  const open = () => { if (dialog.open) return; hide(); opener = document.activeElement; dialog.showModal(); dialog.querySelector('[data-close]').focus({ preventScroll: true }); };
  root.querySelector('[data-cad-shortcuts-open]').addEventListener('click', open);
  document.addEventListener('pointerdown', hide, true); document.addEventListener('scroll', hide, true); window.addEventListener('resize', hide); window.addEventListener('blur', hide);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') hide(); });
  new MutationObserver(hide).observe(root, { attributes: true, attributeFilter: ['data-ux-stage'] });
  return { open };
}

const textEditor = target => Boolean(target?.closest?.('input,textarea,select,[contenteditable],[role="textbox"]'));

export function bindToolbarShortcuts({ root, svg, canvasController, transforms }) {
  const guidance = bindGuidance(root, svg);
  let composing = false;
  const editable = () => root.isConnected && !canvasController.getState().readOnly && root.dataset.uxStage === 'build';
  const notice = text => { const box = root.querySelector('[data-cad-shortcut-notice]'); box.textContent = text; box.hidden = !text; };
  const idle = () => !(transforms?.active() || canvasController.getState().cad?.activeCommand !== 'SELECT');
  let observedDraft = canvasController.getState().draft;
  canvasController.subscribeStateChange(state => { if (state.draft !== observedDraft) { observedDraft = state.draft; notice(''); } });
  root.addEventListener('input', () => notice(''));
  root.addEventListener('click', event => { if (!event.target.closest?.('#workspace-save')) notice(''); });

  const syncSaveAccess = () => { const button = root.querySelector('#workspace-save'); button.disabled = !editable() || button.getAttribute('aria-busy') === 'true'; };
  new MutationObserver(() => { syncSaveAccess(); notice(''); }).observe(root, { attributes: true, attributeFilter: ['data-ux-stage'] });
  syncSaveAccess();
  root.addEventListener('compositionstart', () => { composing = true; });
  root.addEventListener('compositionend', () => { composing = false; });
  root.addEventListener('focusout', () => { composing = false; });
  window.addEventListener('blur', () => { composing = false; });
  const handleKey = event => {
    if (!(event.key.toLowerCase() === 's' && (event.ctrlKey || event.metaKey))) notice('');
    if (event.defaultPrevented || !editable() || composing || event.isComposing || event.keyCode === 229 || event.altKey) return;
    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === 's') {
      event.preventDefault(); event.stopPropagation();
      const save = root.querySelector('#workspace-save');
      if (event.repeat || save.disabled) return;
      const pending = !idle() || canvasController.getState().cad?.gripPreview;
      notice((pending ? '当前命令尚未完成，预览不会保存；仅保存已提交的模型。' : '') +
        (!canvasController.getState().dirty ? '当前没有未保存修改。' : ''));
      save.click();
      return;
    }
    const plain = !event.ctrlKey && !event.metaKey && !event.shiftKey;
    const fallback = event.target.matches?.('[data-cad-transform-command]') && event.key === 'Enter' && plain && idle()
      ? AIDS.find(row => row[2] === event.target.value.trim().toUpperCase()) : null;
    if (fallback) {
      event.preventDefault(); event.stopPropagation();
      if (!event.repeat) { event.target.value = ''; root.querySelector(`[data-cad-${fallback[0]}]`)?.click(); svg.focus({ preventScroll: true }); }
      return;
    }
    if (textEditor(event.target)) return;
    if (event.key === '?' && !event.ctrlKey && !event.metaKey && idle() && (event.target === svg || svg.contains(event.target))) {
      event.preventDefault(); event.stopPropagation(); if (!event.repeat) guidance.open(); return;
    }
    let control = plain ? AIDS.find(row => row[1] === event.key)?.[0] : null;
    if ((event.ctrlKey || event.metaKey) && ['z','y'].includes(event.key.toLowerCase())) {
      if (event.key.toLowerCase() === 'z') control = event.shiftKey ? 'redo' : 'undo';
      else if (!event.shiftKey) control = 'redo';
    }
    if (!control) return;
    event.preventDefault(); event.stopPropagation();
    if (!event.repeat) root.querySelector(`[data-cad-${control}]`)?.click();
  };
  root.addEventListener('keydown', handleKey, true);
  // A newly loaded Workspace has BODY focus before any Canvas interaction.
  document.addEventListener('keydown', event => {
    if (event.target === document.body && root.isConnected && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') handleKey(event);
  }, true);
}
