const stable = (state) => ({ state: state.state, fieldIndex: state.state === "DYNAMIC_INPUT" ? state.fieldIndex : null });
const result = (state, fieldIndex = null) => ({ state, fieldIndex });
const point = (value) => value && Number.isFinite(value.x) && Number.isFinite(value.y);

export function transition(state, event) {
  const current = stable(state);
  if (event.type === "SELECT_TOOL") return result({ SELECT: "SELECTING", NODE: "DRAW_NODE", MEMBER: "DRAW_MEMBER_WAIT_START" }[event.tool] || current.state);
  if (event.type === "ESC") return result("IDLE");
  if (event.type === "TAB") return current.state === "DYNAMIC_INPUT" ? result("DYNAMIC_INPUT", current.fieldIndex === 0 ? 1 : 0) : current;
  if (event.type === "ENTER") {
    if (!event.valid || ((current.state === "DRAW_NODE" || current.state === "DRAW_MEMBER_WAIT_START" || current.state === "DRAW_MEMBER_WAIT_END" || current.state === "DYNAMIC_INPUT") && !point(event.point))) return current;
    if (current.state === "DRAW_MEMBER_WAIT_START") return result("DRAW_MEMBER_WAIT_END");
    if (current.state === "DRAW_MEMBER_WAIT_END" || current.state === "DYNAMIC_INPUT") return result("DRAW_MEMBER_WAIT_START");
    return current;
  }
  if (event.type === "POINTER_POINT") {
    if (!point(event.point)) return current;
    if (current.state === "DRAW_MEMBER_WAIT_START") return result("DRAW_MEMBER_WAIT_END");
    if (current.state === "DRAW_MEMBER_WAIT_END") return result("DRAW_MEMBER_WAIT_START");
    return current;
  }
  if (event.type === "INPUT_CHANGE" && event.mode === "DYNAMIC" && (event.field === "DISTANCE" || event.field === "ANGLE") && (current.state === "DRAW_MEMBER_WAIT_END" || current.state === "DYNAMIC_INPUT")) return result("DYNAMIC_INPUT", event.field === "DISTANCE" ? 0 : 1);
  return current;
}
