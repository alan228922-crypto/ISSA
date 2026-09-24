const NS = "http://www.w3.org/2000/svg";

function numeric(form, name) {
  const value = form.elements.namedItem(name)?.value;
  if (value == null || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function draw(svg, rectangles, dimensioned = false) {
  svg.replaceChildren();
  const vertices = rectangles.flatMap(({ width_mm: w, height_mm: h, center_x_mm: x = 0, center_y_mm: y = 0, angle_deg: a = 0 }) => {
    const radians = a * Math.PI / 180;
    return [[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]].map(([dx,dy]) => [x + dx*Math.cos(radians)-dy*Math.sin(radians), y + dx*Math.sin(radians)+dy*Math.cos(radians)]);
  });
  const xs = vertices.map(v => v[0]), ys = vertices.map(v => v[1]);
  const left = Math.min(...xs), right = Math.max(...xs), bottom = Math.min(...ys), top = Math.max(...ys);
  const pad = Math.max(right-left, top-bottom, 1) * .15;
  svg.setAttribute("viewBox", `${left-pad} ${-top-pad} ${right-left+2*pad} ${top-bottom+2*pad}`);
  rectangles.forEach(({ width_mm: w, height_mm: h, center_x_mm: x = 0, center_y_mm: y = 0, angle_deg: a = 0 }) => {
    const rect = document.createElementNS(NS, "rect");
    for (const [key,value] of Object.entries({ x:x-w/2, y:-y-h/2, width:w, height:h, transform:`rotate(${-a} ${x} ${-y})`, fill:"#86b6d7", stroke:"#17324a" })) rect.setAttribute(key, String(value));
    svg.append(rect);
  });
  if (dimensioned) {
    const { width_mm: w, height_mm: h } = rectangles[0];
    function element(tag, attributes, content = "") {
      const node = document.createElementNS(NS, tag);
      for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
      node.textContent = content;
      svg.append(node);
    }
    const style = { fill: "#17324a", "font-size": pad * .55, "text-anchor": "middle" };
    element("line", { x1: -w/2, y1: h/2 + pad*.35, x2: w/2, y2: h/2 + pad*.35, stroke: "#17324a", "stroke-width": pad*.04 });
    element("text", { x: 0, y: h/2 + pad*.85, ...style }, `${w} mm`);
    element("line", { x1: -w/2-pad*.35, y1: -h/2, x2: -w/2-pad*.35, y2: h/2, stroke: "#17324a", "stroke-width": pad*.04 });
    element("text", { x: -w/2-pad*.7, y: 0, transform: `rotate(-90 ${-w/2-pad*.7} 0)`, ...style }, `${h} mm`);
  }
}

function showProperties(target, values) {
  target.replaceChildren();
  for (const [label,key,unit] of [["面积 A","A_mm2","mm²"],["形心 X","centroid_x_mm","mm"],["形心 Y","centroid_y_mm","mm"],["Ix","Ix_mm4","mm⁴"],["Iy","Iy_mm4","mm⁴"],["线质量","mass_per_length_g_per_mm","g/mm"],["强轴","strong_axis",""],["弱轴","weak_axis",""]]) {
    const dt = document.createElement("dt"), dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = `${values[key]} ${unit}`.trim();
    target.append(dt,dd);
  }
}

function rectangleDefinition(form) {
  const width_mm = numeric(form,"width_mm"), height_mm = numeric(form,"height_mm"), density_g_per_mm3 = numeric(form,"density_g_per_mm3");
  if (width_mm === null || height_mm === null || density_g_per_mm3 === null || width_mm <= 0 || height_mm <= 0 || density_g_per_mm3 < 0) return null;
  return { schema_version:"section-definition-v1", type:"rectangle", width_mm, height_mm, density_g_per_mm3 };
}

function compositeDefinition(root) {
  const components = [];
  for (const row of root.querySelectorAll("[data-component-row]")) {
    if (row.hidden || row.querySelector('[name$="-DELETE"]')?.checked) continue;
    const values = {};
    for (const field of ["width_mm", "height_mm", "center_x_mm", "center_y_mm", "angle_deg", "density_g_per_mm3"]) {
      const input = row.querySelector(`[name$="-${field}"]`);
      if (!input || input.value.trim() === "") return null;
      values[field] = Number(input.value);
      if (!Number.isFinite(values[field])) return null;
    }
    if (values.width_mm <= 0 || values.height_mm <= 0 || values.density_g_per_mm3 < 0) return null;
    components.push(values);
  }
  return components.length ? { schema_version:"section-definition-v1", type:"composite", components } : null;
}

const presets = {
  h: [[60,10,0,45],[10,80,0,0],[60,10,0,-45]],
  t: [[60,10,0,40],[10,80,0,-5]],
  box: [[60,10,0,45],[10,80,-25,0],[10,80,25,0],[60,10,0,-45]],
};

function bindRows(root, form, update) {
  const container = root.querySelector("[data-component-rows]");
  const total = form.elements.namedItem("components-TOTAL_FORMS");
  const initial = Number(form.elements.namedItem("components-INITIAL_FORMS").value);
  function add(values) {
    const index = Number(total.value);
    const template = root.querySelector("[data-empty-component]");
    const wrapper = document.createElement("div");
    wrapper.innerHTML = template.innerHTML.replaceAll("__prefix__", String(index));
    const row = wrapper.firstElementChild;
    row.querySelector("legend").textContent = `矩形组件 ${index + 1}`;
    container.append(row);
    total.value = String(index + 1);
    if (values) {
      for (const [field, value] of Object.entries(values)) row.querySelector(`[name$="-${field}"]`).value = String(value);
    }
    update();
    return row;
  }
  root.querySelector("[data-add-component]").addEventListener("click", () => add());
  container.addEventListener("click", event => {
    if (!event.target.closest("[data-remove-component]")) return;
    const row = event.target.closest("[data-component-row]");
    const checkbox = row.querySelector('[name$="-DELETE"]');
    checkbox.checked = true;
    row.hidden = true;
    update();
  });
  root.querySelectorAll("[data-section-preset]").forEach(button => button.addEventListener("click", () => {
    const layout = presets[button.dataset.sectionPreset];
    if (!layout) return;
    for (const row of container.querySelectorAll("[data-component-row]")) row.remove();
    total.value = "0";
    // Example buttons only exist on the create page; no persisted initial forms are replaced.
    if (initial !== 0) return;
    for (const [width_mm,height_mm,center_x_mm,center_y_mm] of layout) add({width_mm,height_mm,center_x_mm,center_y_mm,angle_deg:0,density_g_per_mm3:.0007});
  }));
}

export function bindSectionDesigner(root) {
  const form = root.querySelector("form"), svg = root.querySelector("[data-section-preview-svg]"), properties = root.querySelector("[data-section-properties]"), status = root.querySelector("[data-section-preview-status]");
  let token = 0;
  let timer;
  function schedule() {
    ++token;
    clearTimeout(timer);
    properties.replaceChildren();
    svg.replaceChildren();
    timer = setTimeout(update, 180);
  }
  async function update() {
    const current = ++token;
    properties.replaceChildren();
    svg.replaceChildren();
    const definition = root.dataset.sectionDesigner === "composite" ? compositeDefinition(root) : rectangleDefinition(form);
    if (!definition) { status.textContent = "请输入有效的正数尺寸和非负密度。"; return; }
    draw(svg,definition.type === "composite" ? definition.components : [definition],definition.type === "rectangle");
    status.textContent = "正在计算截面属性…";
    try {
      const response = await fetch(root.dataset.previewUrl, { method:"POST", credentials:"same-origin", headers:{ "Content-Type":"application/json", "X-CSRFToken":form.elements.namedItem("csrfmiddlewaretoken").value }, body:JSON.stringify(definition) });
      const result = await response.json();
      if (current !== token) return;
      if (!response.ok || !result.ok) { status.textContent = result.error?.message || "截面预览失败，请检查输入。"; return; }
      showProperties(properties,result.properties);
      status.textContent = "截面属性已更新；尚未保存。";
    } catch (_) { if (current === token) status.textContent = "无法取得截面预览，请稍后重试。"; }
  }
  form.addEventListener("input",schedule);
  form.addEventListener("change",schedule);
  if (root.dataset.sectionDesigner === "composite") bindRows(root,form,schedule);
  schedule();
}

document.querySelectorAll("[data-section-designer]").forEach(bindSectionDesigner);
