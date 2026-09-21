const INITIAL = Object.freeze({ model: "active", prediction: "optional", analysis: "pending", understanding: "pending", reflection: "optional" });

export function createWorkflowProgress(root) {
  const states = { ...INITIAL };
  const paint = () => {
    for (const item of root.querySelectorAll("[data-workflow-step]")) {
      item.dataset.state = states[item.dataset.workflowStep] || "pending";
      item.setAttribute("aria-current", item.dataset.state.startsWith("active") ? "step" : "false");
    }
  };
  const set = (step, state) => { states[step] = state; paint(); };
  paint();
  return Object.freeze({
    saved() { set("model", "completed"); if (["optional", "pending"].includes(states.prediction)) set("prediction", "active-optional"); },
    prediction(status) { set("prediction", status === "COMPLETED" ? "completed" : status === "SKIPPED" ? "completed-optional" : "active-optional"); },
    analyzed() { set("model", "completed"); if (states.prediction !== "completed") set("prediction", "completed-optional"); set("analysis", "completed"); set("understanding", "active"); },
    understood() { set("understanding", "completed"); if (states.reflection !== "completed") set("reflection", "active-optional"); },
    reflection(status) { set("reflection", status === "COMPLETED" ? "completed" : status === "DRAFT" ? "active-optional" : "optional"); },
    state: () => Object.freeze({ ...states }),
  });
}
