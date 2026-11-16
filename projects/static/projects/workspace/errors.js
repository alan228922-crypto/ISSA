export function normalizeApiError(response) {
  const error = response?.error || response || {};
  return { code: error.code || "REQUEST_FAILED", message: error.message || "请求暂时无法完成。", details: error.details || {} };
}

export function presentWorkspaceError(error) {
  const normalized = normalizeApiError(error);
  if (normalized.code === "CAD_INPUT_MALFORMED" && normalized.details.input_context === "NODE_DIRECT_XY_ENTRY") return { what: "节点坐标未完成", why: "请输入完整的绝对坐标 X,Y，例如 120,350；支持负数和小数。", nextAction: "修正坐标后按 Enter 确认。" };
  if (normalized.code === "EDITOR_DEPENDENCY_CONFLICT") return { what: "暂时不能删除这个对象", why: "模型中还有其他对象依赖它。", nextAction: "请先删除或调整依赖该对象的构件、连接、支座或荷载。", technicalCode: normalized.code };
  if (["SINGULAR_GLOBAL_STIFFNESS", "UNSTABLE_MODEL"].includes(normalized.code)) return { what: "当前模型还不能完成分析", why: "模型可能存在整体稳定性或约束不足，但仅凭这一提示不能确定唯一原因。", nextAction: "请依次检查支座、连接、孤立节点和整体稳定性，再运行模型检查。", technicalCode: normalized.code };
  if (normalized.code === "STALE_DRAFT") return { what: "无法保存当前模型", why: "当前模型版本已发生变化，请重新加载后再继续。", nextAction: "重新加载页面后再继续编辑。", technicalCode: normalized.code };
  if (normalized.code === "PREDICTION_AMBIGUOUS") return { what: "预测记录暂时无法使用", why: "当前预测记录存在数据歧义，暂时无法继续使用预测。请联系管理员处理。", nextAction: "请联系管理员处理后再继续。", technicalCode: normalized.code };
  if (normalized.code === "REQUEST_FAILED") return { what: "当前操作未完成", why: "网络或服务器暂时不可用。", nextAction: "请检查网络连接后重试。", technicalCode: normalized.code };
  const safe = {
    UNSAVED_DRAFT: "本地修改尚未保存，请先保存模型。",
    EDITOR_NODE_MOVE_ZERO_LENGTH: "此位置会使构件长度为零，原节点未移动。",
    EDITOR_NODE_MOVE_BREAKS_CONNECTION: "移动会使连接脱离构件，原节点未移动。",
    STALE_DELETE_PREVIEW: "模型已发生变化，请重新执行删除。",
    EDITOR_EXPLICIT_NODE_REQUIRED: "此处已有节点，请通过节点捕捉明确选择节点。",
    EDITOR_UNJOINED_CROSSING_ENDPOINT: "此处是尚未连接的构件交点；请先用「节点」工具建立连接。",
    EDITOR_DUPLICATE_PARTICIPANT: "该构件已在此连接中参与，请选择其他构件。",
    MEMBER_PROPERTIES_REQUIRED: "请选择新构件使用的材料和截面。",
    CAD_COMMAND_CONTEXT: "请先选择节点或构件工具。",
    CAD_INPUT_MALFORMED: "输入格式无效，请输入有效的坐标、长度或角度；可输入 x,y、@dx,dy 或 长度<角度。",
    CAD_INPUT_EMPTY: "请输入坐标、长度或角度后再确认。",
    CAD_INPUT_INCOMPLETE: "坐标、长度或角度尚未输入完整，请补齐后再确认。",
    NODE_MOVE_CONFLICT: "目标位置已有节点，请换一个位置；原节点未移动。",
    NODE_NOT_ON_MEMBER: "此节点未连接构件；请先绘制构件。",
    MULTIPLE_JOINTS_AT_NODE: "此节点有多个旧连接，无法确定支座或荷载目标；请先整理模型。",
    RUN_NOT_DISCOVERED: "请选择列表中的分析记录。",
    REPORT_RUN_REQUIRED: "请先选择一次分析记录。",
  };
  return { what: "当前操作未完成", why: Object.hasOwn(safe, normalized.code) ? safe[normalized.code] : "暂时无法完成这项操作。", nextAction: "请检查模型后重试；若仍无法完成，请联系管理员。" };
}

export function renderWorkspaceError(root, error) {
  const view = presentWorkspaceError(error);
  root.hidden = false;
  root.replaceChildren();
  const what = document.createElement("h3"); what.dataset.errorWhat = ""; what.textContent = view.what;
  const why = document.createElement("p"); why.dataset.errorWhy = ""; why.textContent = `原因：${view.why}`;
  const next = document.createElement("p"); next.dataset.errorNext = ""; next.textContent = `下一步：${view.nextAction}`;
  root.append(what, why, next);
  return view;
}
