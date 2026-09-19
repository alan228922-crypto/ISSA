export function normalizeApiError(response) {
  const error = response?.error || response || {};
  return { code: error.code || "REQUEST_FAILED", message: error.message || "请求暂时无法完成。", details: error.details || {} };
}

export function presentWorkspaceError(error) {
  const normalized = normalizeApiError(error);
  if (normalized.code === "STALE_DRAFT") return { what: "无法保存当前模型", why: "当前模型版本已发生变化，请重新加载后再继续。", nextAction: "重新加载页面后再继续编辑。", technicalCode: normalized.code };
  if (normalized.code === "PREDICTION_AMBIGUOUS") return { what: "预测记录暂时无法使用", why: "当前预测记录存在数据歧义，暂时无法继续使用预测。请联系管理员处理。", nextAction: "请联系管理员处理后再继续。", technicalCode: normalized.code };
  if (normalized.code === "REQUEST_FAILED") return { what: "当前操作未完成", why: "网络或服务器暂时不可用。", nextAction: "请检查网络连接后重试。", technicalCode: normalized.code };
  return { what: "当前操作未完成", why: normalized.message, nextAction: "请根据提示检查后重试。", technicalCode: normalized.code };
}
