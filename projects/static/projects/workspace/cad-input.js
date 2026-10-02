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

export function parseDynamicPoint({mode,values,origin}) {
  const keys={XY:['x','y'],POLAR:['length','angle'],RELATIVE:['dx','dy']}[mode];
  if(!keys||!values)return {ok:false,code:'MALFORMED'};
  const raw=keys.map(k=>typeof values[k]==='string'?values[k].trim():null);
  if(raw.some(v=>v===null))return {ok:false,code:'MALFORMED'};
  if(raw.every(v=>v===''))return {ok:false,code:'EMPTY'};
  if(raw.some(v=>v===''))return {ok:false,code:'INCOMPLETE'};
  const numeric=/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;
  const [first,second]=raw.map(Number);
  if(!raw.every(v=>numeric.test(v))||!finite([first,second]))return {ok:false,code:'MALFORMED'};
  if(mode==='XY')return {ok:true,point:{x:first,y:second}};
  if(!origin||!finite([origin.x,origin.y])||(mode==='POLAR'&&first<=0))return {ok:false,code:'MALFORMED'};
  const radians=second*Math.PI/180;
  const point=mode==='RELATIVE'?{x:origin.x+first,y:origin.y+second}:{x:origin.x+first*Math.cos(radians),y:origin.y+first*Math.sin(radians)};
  return finite([point.x,point.y])?{ok:true,point}:{ok:false,code:'MALFORMED'};
}
