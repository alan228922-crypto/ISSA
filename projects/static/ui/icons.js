// 同一正式SVG sprite；仅负责呈现，不接管按钮事件。
export function createUiIcon(name) {
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('class','ui-icon');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');
  const use=document.createElementNS(svg.namespaceURI,'use');use.setAttribute('href',new URL(`./icons.svg#${name}`,import.meta.url).href);svg.append(use);return svg;
}
