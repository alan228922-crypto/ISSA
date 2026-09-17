const number = "[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)";
const coordinate = new RegExp(`^(${number})\\s*,\\s*(${number})$`);
const relative = new RegExp(`^@\\s*(${number})\\s*,\\s*(${number})$`);
const polar = new RegExp(`^(${number})\\s*<\\s*(${number})$`);

function failure(text) {
  if (!text.trim()) return { ok: false, code: "EMPTY" };
  if (/[@<,]$/.test(text.trim()) || /^@?\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)?\s*,\s*$/.test(text)) return { ok: false, code: "INCOMPLETE" };
  return { ok: false, code: "MALFORMED" };
}

function finite(values) { return values.every(Number.isFinite); }

export function parseCadInput(text, origin) {
  if (typeof text !== "string") return { ok: false, code: "MALFORMED" };
  const value = text.trim(); let match;
  if ((match = coordinate.exec(value))) { const [x, y] = match.slice(1).map(Number); return finite([x, y]) ? { ok: true, kind: "ABSOLUTE", point: { x, y } } : failure(value); }
  if ((match = relative.exec(value))) { if (!origin || !finite([origin.x, origin.y])) return { ok: false, code: "MALFORMED" }; const [dx, dy] = match.slice(1).map(Number); const point = { x: origin.x + dx, y: origin.y + dy }; return finite([dx, dy, point.x, point.y]) ? { ok: true, kind: "RELATIVE", point } : failure(value); }
  if ((match = polar.exec(value))) { if (!origin || !finite([origin.x, origin.y])) return { ok: false, code: "MALFORMED" }; const [length, angle] = match.slice(1).map(Number); const radians = angle * Math.PI / 180; const point = { x: origin.x + length * Math.cos(radians), y: origin.y + length * Math.sin(radians) }; return finite([length, angle, point.x, point.y]) ? { ok: true, kind: "POLAR", point } : failure(value); }
  return failure(value);
}
