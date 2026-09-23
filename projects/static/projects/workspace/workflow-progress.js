const BLANK = Object.freeze({ model: "active", prediction: "optional", analysis: "pending", understanding: "pending", reflection: "optional" });

function modelExists(draft) {
  return Number.isInteger(draft?.version) && draft.version > 0 && (draft.physical_members || []).some((member) => member.is_active !== false);
}

function currentSuccessfulRun(runs, draftVersion) {
  return (runs || []).some((run) => run.status === "SUCCESS" && run.is_stale !== true && run.source_draft_version === draftVersion);
}

function selectedCurrentRun(run, draftVersion) {
  return run?.status === "SUCCESS" && run.is_stale !== true && run.source_draft_version === draftVersion;
}

export function projectWorkflow({ draft = null, prediction = null, runs = [], selectedRun = null, reflection = null } = {}) {
  if (!modelExists(draft)) return Object.freeze({ ...BLANK });
  const states = { model: "completed", prediction: "optional", analysis: "pending", understanding: "pending", reflection: "optional" };
  const predictionCompleted = prediction?.state === "COMPLETED";
  const predictionSkipped = prediction?.skipped === true;
  if (!currentSuccessfulRun(runs, draft.version)) {
    if (predictionCompleted) {
      states.prediction = "completed";
      states.analysis = "active";
    } else if (predictionSkipped) {
      states.prediction = "completed-optional";
      states.analysis = "active";
    } else {
      states.prediction = "active-optional";
      states.analysis = "available";
    }
    return Object.freeze(states);
  }
  states.prediction = predictionCompleted ? "completed" : "completed-optional";
  states.analysis = "completed";
  states.understanding = "active";
  if (selectedCurrentRun(selectedRun, draft.version) && reflection?.status === "DRAFT") {
    states.understanding = "completed";
    states.reflection = "active-optional";
  } else if (selectedCurrentRun(selectedRun, draft.version) && reflection?.status === "COMPLETED") {
    states.understanding = "completed";
    states.reflection = "completed";
  }
  return Object.freeze(states);
}

export function createWorkflowProgress(root, initialFacts = {}) {
  let facts = { draft: null, prediction: null, runs: [], selectedRun: null, reflection: null, ...initialFacts };
  let states = projectWorkflow(facts);
  const paint = () => {
    for (const item of root.querySelectorAll("[data-workflow-step]")) {
      item.dataset.state = states[item.dataset.workflowStep] || "pending";
      item.setAttribute("aria-current", item.dataset.state.startsWith("active") ? "step" : "false");
    }
  };
  const project = (patch = {}) => { facts = { ...facts, ...patch }; states = projectWorkflow(facts); paint(); return states; };
  paint();
  return Object.freeze({ project, state: () => Object.freeze({ ...states }), facts: () => Object.freeze({ ...facts }) });
}
