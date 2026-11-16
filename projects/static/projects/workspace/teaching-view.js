import { createStudentLabelResolver } from "./labels.js";

const STATES = new Set(["TENSION", "COMPRESSION", "ZERO_FORCE", "MIXED"]);
const keyOf = (item) => item?.id ?? item?.client_key;
const KNOWN_BLOCKS = new Set(["MEMBER_FORCE_STATE", "MAXIMUM_DISPLACEMENT", "PREDICTION_COMPARISON", "REPRESENTATIVE_LOAD_PATH"]);
const INTERNAL_TEXT = /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b|[a-f0-9]{64}|[a-z]+:[\w:-]+|(?:physical-(?:draft|snapshot)|prediction|comparison|explanation|reflection|truss2d-(?:input|result))-v\d/;

function internalStrings(value, tokens = new Set()) {
  if (!value || typeof value !== "object") return tokens;
  for (const [key, entry] of Object.entries(value)) {
    if (typeof entry === "string" && /(^id$|_id$|_key$|_version$|_hash$|^code$)/.test(key)) tokens.add(entry);
    else if (entry && typeof entry === "object") internalStrings(entry, tokens);
  }
  return tokens;
}

function presentationBlocks(explanation, members, labels, displacement, comparisonAvailable, payload) {
  const tokens = [...internalStrings(payload)];
  const message = (text, fallback) => typeof text === "string" && text.trim()
    && !INTERNAL_TEXT.test(text) && !tokens.some(token => token && text.includes(token))
    && !/正确|错误|答错|失分|评分|得分/.test(text) ? text : fallback;
  return explanation.blocks.filter(block => comparisonAvailable
    || !["PREDICTION_COMPARISON", "REPRESENTATIVE_LOAD_PATH"].includes(block.type)).map(block => {
    if (!KNOWN_BLOCKS.has(block.type)) return { kind: "UNAVAILABLE", label: "结果说明", messages: {
      level_1: "这项说明暂不可用。", level_2: "请查看其他已提供的分析证据。", level_3: "请重新选择分析记录后重试。" }, segments: [], candidates: [] };
    const key = block.subject?.physical_member_client_key;
    const member = members.find(item => item.key === key);
    const isMaximum = block.type === "MAXIMUM_DISPLACEMENT";
    const label = isMaximum ? "最大位移" : member?.label || "构件";
    const source = block.message_zh_CN || {};
    const maximumSummary = displacement.available
      ? `最大位移出现在 ${displacement.candidates.map(item => item.label).join("、")}，大小为 ${displacement.maximumMm} mm。`
      : "最大位移证据暂不可用，请重新选择分析记录后重试。";
    return { kind: block.type, memberKey: member?.key || null, label,
      messages: {
        level_1: isMaximum ? maximumSummary : message(source.level_1, "请对照该构件的分析段受力证据。"),
        level_2: message(source.level_2, isMaximum ? "观察这些位置和相邻构件的变形关系。" : "请对照各分析段的受力状态，说明支持你判断的证据。"),
        level_3: message(source.level_3, "以下数值来自所选分析记录，不是当前草稿的重新计算。"),
      },
      segments: member ? (block.facts?.segments || []).map(segment => ({ ...segment,
        label: labels.analysisMember(key, segment.analysis_member_id) })) : [],
      candidates: isMaximum && displacement.available ? (block.professional_values?.candidates || []).map(candidate => ({
        id: candidate.analysis_node_id, label: labels.analysisNode(candidate.analysis_node_id),
        uxMm: candidate.ux_mm, uyMm: candidate.uy_mm, magnitudeMm: candidate.displacement_mm,
      })) : [],
    };
  });
}

function projectDisplacement(maximum, comparison, snapshot, labels) {
  const unavailable = () => ({ available: false, candidates: [], predictedLocationLabel: null, locationMatch: null });
  const facts = maximum?.facts;
  const ids = facts?.candidate_analysis_node_ids;
  const supplied = maximum?.professional_values;
  if (!Number.isFinite(facts?.maximum_displacement_mm) || facts.maximum_displacement_mm < 0
    || !Array.isArray(ids) || !ids.length || new Set(ids).size !== ids.length
    || !Array.isArray(supplied?.candidates) || supplied.candidates.length !== ids.length
    || supplied.maximum_displacement_mm !== facts.maximum_displacement_mm) return unavailable();
  const rows = new Map(supplied.candidates.map(row => [row.analysis_node_id, row]));
  if (rows.size !== ids.length) return unavailable();
  const candidates = [];
  for (const id of ids) {
    const row = rows.get(id);
    const label = labels.analysisNode(id);
    if (typeof id !== "string" || !row || ["节点", "连接", "分析节点", "构件 起点", "构件 终点"].includes(label)
      || ![row.ux_mm, row.uy_mm, row.displacement_mm].every(Number.isFinite) || row.displacement_mm < 0) return unavailable();
    candidates.push({ id, label, uxMm: row.ux_mm, uyMm: row.uy_mm, magnitudeMm: row.displacement_mm });
  }
  let predictedLocationLabel = null;
  let locationMatch = null;
  if (comparison.comparison_available) {
    const compared = comparison.maximum_displacement;
    if (!compared || compared.maximum_displacement_mm !== facts.maximum_displacement_mm
      || typeof compared.location_match !== "boolean" || !Array.isArray(compared.candidate_analysis_node_ids)
      || compared.candidate_analysis_node_ids.length !== ids.length
      || compared.candidate_analysis_node_ids.some((id, index) => id !== ids[index])) return unavailable();
    const point = compared.predicted_point;
    const nodes = new Set(snapshot.nodes.map(keyOf));
    if (point?.kind === "NODE" && nodes.has(point.node_client_key)) {
      predictedLocationLabel = labels.label("GEOMETRY_NODE", point.node_client_key);
    } else if (point?.kind === "CONNECTION") {
      const connection = snapshot.connections?.find(item => keyOf(item) === point.connection_client_key);
      if (connection && nodes.has(connection.geometry_node_id)) predictedLocationLabel = labels.label("CONNECTION", point.connection_client_key);
    } else if (point?.kind === "MEMBER_ENDPOINT" && ["START", "END"].includes(point.endpoint)) {
      const member = snapshot.physical_members.find(item => keyOf(item) === point.physical_member_client_key);
      if (member && nodes.has(point.endpoint === "START" ? member.start_node_id : member.end_node_id)) {
        predictedLocationLabel = labels.analysisNode(`free:${point.physical_member_client_key}:${point.endpoint}`);
      }
    }
    if (!predictedLocationLabel) return unavailable();
    locationMatch = compared.location_match;
  }
  return { available: true, maximumMm: facts.maximum_displacement_mm, candidates, predictedLocationLabel, locationMatch };
}
const frozen = (value) => {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(frozen);
    Object.freeze(value);
  }
  return value;
};

export function canLinkCanvas(view, workspace) {
  return view.available === true && view.projectId === workspace.projectId
    && view.sourceDraftVersion === workspace.draftVersion && workspace.dirty === false;
}

/** Presentation projection only. Classification and maxima are supplied by the server. */
export function buildTeachingView({ payload, runNumber, workspace }) {
  const unavailable = () => frozen({ available: false, members: [], explanationBlocks: [],
    displacement: { available: false }, comparisonAvailable: false, canLinkCanvas: false,
    historical: true, runNumber, runLabel: `第 ${runNumber} 次分析` });
  if (!payload || payload.status !== "SUCCESS") return unavailable();
  const { metadata, data, comparison, explanation, report: envelope, reflection } = payload;
  const report = envelope?.report;
  const runId = metadata?.analysis_run_id;
  const version = metadata?.source_draft_version;
  const revision = metadata?.model_revision_id;
  if (!Number.isInteger(runId) || !Number.isInteger(version) || !Number.isInteger(revision)
    || !data || !comparison || !explanation || !report?.metadata || !report.provenance
    || data.status !== "SUCCESS" || !data.result_json || !Array.isArray(data.result_json.member_results)
    || explanation.explanation_available !== true) return unavailable();
  const sources = [data, comparison, explanation, report.metadata, report.provenance, reflection].filter(Boolean);
  if (sources.some(source => source.analysis_run_id !== runId
    || (source.project_id !== undefined && source.project_id !== workspace.projectId)
    || (source.source_draft_version !== undefined && source.source_draft_version !== version)
    || (source.model_revision_id !== undefined && source.model_revision_id !== revision))) return unavailable();
  if (report.metadata.project_id !== workspace.projectId || typeof comparison.comparison_available !== "boolean"
    || explanation.comparison_available !== comparison.comparison_available) return unavailable();
  const geometry = report.geometry_connectivity;
  if (!Array.isArray(geometry?.nodes) || !Array.isArray(geometry?.physical_members)
    || !geometry.analysis_member_mapping || !Array.isArray(explanation.blocks)) return unavailable();
  const snapshot = structuredClone(geometry);
  const memberKeys = new Set(snapshot.physical_members.map(keyOf));
  // The report carries the authoritative analysis-segment -> PhysicalMember map.
  // Invert identities for the existing label resolver, without inferring geometry.
  const segmentMap = Object.create(null);
  for (const [segment, member] of Object.entries(snapshot.analysis_member_mapping)) {
    if (typeof member !== "string" || !memberKeys.has(member)) return unavailable();
    (segmentMap[member] ||= []).push(segment);
  }
  snapshot.analysis_member_mapping = segmentMap;
  const labels = createStudentLabelResolver(snapshot);
  const memberBlocks = explanation.blocks.filter(block => block.type === "MEMBER_FORCE_STATE");
  const suppliedKeys = new Set(memberBlocks.map(block => block.subject?.physical_member_client_key));
  if (suppliedKeys.size !== memberBlocks.length || !memberBlocks.length
    || (data.result_json?.member_results || []).some(row => !suppliedKeys.has(row.physical_member_id))) return unavailable();
  const members = [];
  for (const block of memberBlocks) {
    const key = block.subject?.physical_member_client_key;
    const facts = block.facts;
    const mapping = snapshot.analysis_member_mapping[key];
    if (!memberKeys.has(key) || !STATES.has(facts?.actual_state) || !Array.isArray(facts.segments)
      || !facts.segments.length || !Array.isArray(mapping)
      || facts.segments.some(segment => !mapping.includes(segment.analysis_member_id)
        || !STATES.has(segment.teaching_state) || !Number.isFinite(segment.axial_force_N))) return unavailable();
    members.push({ key, label: labels.label("PHYSICAL_MEMBER", key), actualState: facts.actual_state,
      segments: facts.segments.map(segment => ({ ...segment, label: labels.analysisMember(key, segment.analysis_member_id) })),
      predictedState: null, comparisonStatus: null });
  }
  const maximum = explanation.blocks.find(block => block.type === "MAXIMUM_DISPLACEMENT");
  const hypothesis = [];
  if (comparison.comparison_available) {
    if (!Array.isArray(comparison.member_comparisons) || !Array.isArray(comparison.load_path_evidence)) return unavailable();
    const sameSegments = (segments, member) => Array.isArray(segments) && segments.length === member.segments.length
      && segments.every((segment, index) => ["analysis_member_id", "teaching_state", "axial_force_N"].every(field => segment[field] === member.segments[index][field]));
    const judged = new Set();
    for (const item of comparison.member_comparisons) {
      const member = members.find(row => row.key === item.physical_member_client_key);
      if (!member || judged.has(member.key) || !["MATCH", "MISMATCH", "UNSURE", "NOT_COMPARABLE"].includes(item.comparison_status)
        || !["TENSION", "COMPRESSION", "ZERO_FORCE", "UNSURE"].includes(item.predicted_state)
        || item.actual?.actual_state !== member.actualState || !sameSegments(item.actual?.segments, member)) return unavailable();
      judged.add(member.key);
      member.predictedState = item.predicted_state;
      member.comparisonStatus = item.comparison_status;
    }
    for (const item of comparison.load_path_evidence) {
      const member = members.find(row => row.key === item.physical_member_client_key);
      if (!member || item.actual_state !== member.actualState || !sameSegments(item.segments, member)) return unavailable();
      hypothesis.push({ key: member.key, label: member.label, actualState: item.actual_state,
        segments: item.segments.map(segment => ({ ...segment, label: labels.analysisMember(member.key, segment.analysis_member_id) })) });
    }
  }
  const displacement = projectDisplacement(maximum, comparison, snapshot, labels);
  const view = { available: true, projectId: workspace.projectId, runId, runNumber,
    runLabel: `第 ${runNumber} 次分析`, sourceDraftVersion: version,
    historical: version !== workspace.draftVersion || workspace.dirty !== false,
    labels, members, explanationBlocks: presentationBlocks(explanation, members, labels, displacement, comparison.comparison_available, payload), displacement,
    comparisonAvailable: comparison.comparison_available, hypothesis };
  view.canLinkCanvas = canLinkCanvas(view, workspace);
  return frozen(view);
}
