import { pickAt, renderedObjectsFromSvg } from './canvas-interaction.js';

export function bindCanvasContextMenu({root, svg, canvasController, transforms}) {
  if (!transforms) return;
  let menu = null;
  const close = (focus = false) => { menu?.remove(); menu = null; if (focus) svg.focus({preventScroll:true}); };
  const select = target => {
    const state = canvasController.getState();
    if (!state.selectedObjects.some(row => row.kind === target.kind && row.clientKey === target.clientKey)) {
      canvasController.replaceState({...state, selectedObjects:[target], selectedObject:target, focusedObject:null});
    }
  };
  svg.addEventListener('contextmenu', event => {
    if (!transforms.available() || event.target.closest?.('input,textarea,select,[contenteditable]')) return;
    event.preventDefault(); close();
    const state = canvasController.getState();
    const gripKey = event.target.closest?.('[data-cad-node-grip]')?.getAttribute('data-cad-node-grip');
    const hit = gripKey ? {kind:'GEOMETRY_NODE',clientKey:gripKey} : pickAt({x:event.clientX,y:event.clientY}, renderedObjectsFromSvg(svg));
    if (!transforms.active() && ['PHYSICAL_MEMBER','GEOMETRY_NODE'].includes(hit?.kind)) select(hit);
    menu = document.createElement('div'); menu.dataset.cadContextMenu = ''; menu.setAttribute('role','menu'); menu.setAttribute('aria-label','画布操作');
    const item = (text, enabled, action) => {
      const button = document.createElement('button'); button.type = 'button'; button.setAttribute('role','menuitem'); button.textContent = text; button.disabled = !enabled;
      button.addEventListener('click', () => { close(); action(); }); menu.append(button);
    };
    if (transforms.active()) {
      item('确认', transforms.canApply(), transforms.confirm);
      item('结束命令', true, transforms.finish); item('取消', true, transforms.cancel);
    } else if (hit?.kind === 'PHYSICAL_MEMBER') {
      for (const [text,code] of [['复制','CO'],['平移','M'],['旋转','RO'],['拉伸','ST'],['修改长度','LEN']]) item(text, code !== 'LEN' || canvasController.getState().selectedObjects.filter(row => row.kind === 'PHYSICAL_MEMBER').length === 1, () => transforms.start(code));
      item('取消选取', true, () => root.querySelector('[data-cad-clear-selection]').click());
    } else if (hit?.kind === 'GEOMETRY_NODE') {
      item('移动节点', true, () => transforms.start('ST',hit.clientKey));
      item('输入坐标', true, () => transforms.start('ST',hit.clientKey));
    } else {
      item('粘贴', transforms.hasClipboard(), transforms.paste);
      for (const [text,selector] of [['复原','[data-cad-undo]'],['重做','[data-cad-redo]'],['适合视窗','[data-cad-fit]']]) {
        const control = root.querySelector(selector); item(text, Boolean(control && !control.disabled), () => control.click());
      }
    }
    const panel = menu;
    panel.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true); return; }
      if (event.key === 'Tab') { close(true); return; }
      if (!['ArrowDown','ArrowUp','Home','End'].includes(event.key)) return;
      event.preventDefault(); event.stopPropagation();
      const items = [...panel.querySelectorAll('button:not(:disabled)')]; if (!items.length) return;
      const index = items.indexOf(document.activeElement);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length-1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items[next].focus();
    });
    document.body.append(panel);
    const bounds = panel.getBoundingClientRect();
    panel.style.left = `${Math.max(8,Math.min(event.clientX,innerWidth-bounds.width-8))}px`;
    panel.style.top = `${Math.max(8,Math.min(event.clientY,innerHeight-bounds.height-8))}px`;
    panel.querySelector('button:not(:disabled)')?.focus({preventScroll:true});
  });
  document.addEventListener('pointerdown', event => { if (menu && !menu.contains(event.target)) close(); },true);
  window.addEventListener('resize', () => close()); window.addEventListener('blur', () => close());
  canvasController.subscribeStateChange(() => close());
  new MutationObserver(() => close()).observe(root,{attributes:true,attributeFilter:['data-ux-stage']});
}
