function inside(rect, point) {
  return point.x >= rect.left && point.x <= rect.right && point.y >= rect.top && point.y <= rect.bottom;
}

function intersects(rect, start, end) {
  if (inside(rect, start) || inside(rect, end)) return true;
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  let enter = 0;
  let leave = 1;
  for (const [p, q] of [[-dx, start.x - rect.left], [dx, rect.right - start.x], [-dy, start.y - rect.top], [dy, rect.bottom - start.y]]) {
    if (p === 0) { if (q < 0) return false; continue; }
    const t = q / p;
    if (p < 0) enter = Math.max(enter, t);
    else leave = Math.min(leave, t);
    if (enter > leave) return false;
  }
  return true;
}

export function objectsInMarquee(rect, renderedObjects, mode) {
  return renderedObjects.filter((item) => {
    const hit = item.hit;
    if (hit?.type === "POINT") return inside(rect, hit.point);
    if (hit?.type !== "SEGMENT") return false;
    return mode === "WINDOW" ? inside(rect, hit.start) && inside(rect, hit.end) : intersects(rect, hit.start, hit.end);
  }).map(({kind, clientKey}) => ({kind, clientKey}));
}
