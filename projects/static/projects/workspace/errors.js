export function normalizeApiError(response) {
  const error = response?.error || response || {};
  return { code: error.code || "REQUEST_FAILED", message: error.message || "请求暂时无法完成。", details: error.details || {} };
}

export function presentWorkspaceError(error) {
  const normalized = normalizeApiError(error);
  if (normalized.code === "EDITOR_DEPENDENCY_CONFLICT") return { what: "暂时不能删除这个对象", why: "模型中还有其他对象依赖它。", nextAction: "请先删除或调整依赖该对象的构件、连接、支座或荷载。", technicalCode: normalized.code };
  if (["SINGULAR_GLOBAL_STIFFNESS", "UNSTABLE_MODEL"].includes(normalized.code)) return { what: "当前模型还不能完成分析", why: "模型可能存在整体稳定性或约束不足，但仅凭这一提示不能确定唯一原因。", nextAction: "请依次检查支座、连接、孤立节点和整体稳定性，再运行模型检查。", technicalCode: normalized.code };
  if (normalized.code === "STALE_DRAFT") return { what: "无法保存当前模型", why: "当前模型版本已发生变化，请重新加载后再继续。", nextAction: "重新加载页面后再继续编辑。", technicalCode: normalized.code };
  if (normalized.code === "PREDICTION_AMBIGUOUS") return { what: "预测记录暂时无法使用", why: "当前预测记录存在数据歧义，暂时无法继续使用预测。请联系管理员处理。", nextAction: "请联系管理员处理后再继续。", technicalCode: normalized.code };
  if (normalized.code === "REQUEST_FAILED") return { what: "当前操作未完成", why: "网络或服务器暂时不可用。", nextAction: "请检查网络连接后重试。", technicalCode: normalized.code };
  return { what: "当前操作未完成", why: normalized.message, nextAction: "请根据提示检查后重试。", technicalCode: normalized.code };
}

export function renderWorkspaceError(root, error) {
  const view = presentWorkspaceError(error);
  root.hidden = false;
  root.replaceChildren();
  const what = document.createElement("h3"); what.dataset.errorWhat = ""; what.textContent = view.what;
  const why = document.createElement("p"); why.dataset.errorWhy = ""; why.textContent = `原因：${view.why}`;
  const next = document.createElement("p"); next.dataset.errorNext = ""; next.textContent = `下一步：${view.nextAction}`;
  const technical = document.createElement("details"); technical.dataset.errorTechnical = "";
  const summary = document.createElement("summary"); summary.textContent = "技术信息";
  const code = document.createElement("code"); code.textContent = view.technicalCode;
  technical.append(summary, code);
  root.append(what, why, next, technical);
  return view;
}
