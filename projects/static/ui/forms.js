// 仅提交反馈，不接管表单验证、字段值或服务端提交。
const pending = new Map();
document.addEventListener('submit', event => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.matches('[data-ui-form]') || event.defaultPrevented) return;
  form.setAttribute('aria-busy', 'true');
  const controls = [...form.querySelectorAll('button[type="submit"],button:not([type]),input[type="submit"]')];
  pending.set(form, controls.map(control => [control, control.disabled]));
  // 不在FormData生成前禁用submitter，避免遗漏原有命名提交值。
  setTimeout(() => { if (form.isConnected) controls.forEach(control => { control.disabled = true; }); }, 0);
});
window.addEventListener('pageshow', () => {
  for (const [form, controls] of pending) {
    form.removeAttribute('aria-busy');
    for (const [control, disabled] of controls) control.disabled = disabled;
  }
  pending.clear();
});
