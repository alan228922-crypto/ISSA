# Reflection and Rationale Architecture — M4C

## Status and scope

- Status: **CONFIRMED — M4C Gate 0A architecture freeze**
- Parent authority: `MASTER_SPEC.md`
- Schema: `reflection-v1`
- Scope: student learning evidence after analysis; no UI, AI workflow, research protocol workflow, score, grade, ranking, or mechanics authority. The frozen M4C HTTP boundary is documented in `API_AND_APPLICATION_FLOW.md` §4.4.3.

Reflection completes the teaching path without becoming an Analyze gate:

```text
Prediction present: Predict → Analyze → Explain → Compare → Reflect
Prediction absent:          Analyze → Explain → Reflect
```

Reflection is a **Soft Gate**. An absent or incomplete Reflection never blocks model editing, draft save, a new Analyze call, or any other core workflow. A future research/task protocol may require a completed Reflection independently; it must not turn core Analyze into a hard gate.

## Authoritative aggregate

`Reflection` is the sole M4C P0 learning-evidence aggregate and integrates P0 Design Rationale. There is no separate `DesignRationale` model/domain, second lifecycle, or `DesignIteration` domain. If an independent rationale aggregate is needed later, it requires a new architecture decision.

```text
AnalysisRun 1 ── 0..1 Reflection
```

`analysis_run` is the primary binding. `source_draft_version` is not a Reflection identity, but remains traceable through:

```text
Reflection.analysis_run → ModelRevision.source_draft_version
```

The conceptual persisted fields are:

```text
Reflection
- id
- analysis_run_id                         unique
- created_by_id
- status                                  DRAFT | COMPLETED
- original_reasoning                      nullable text
- unexpected_results                      nullable text
- next_iteration_intent                   nullable text; P0 Design Rationale
- reflection_schema_version               reflection-v1
- created_at
- updated_at
- completed_at                            nullable
```

The three fields retain student-originated text only:

1. `original_reasoning` — “我原本是怎么判断这个结构的？”
2. `unexpected_results` — “哪些分析结果和我的预想不同？”
3. `next_iteration_intent` — “下一版我想修改什么，或重新观察什么？” It is the P0 Design Rationale.

All user-facing prompts and errors are zh-CN. There is no rich text, attachment, upload, comparison set, result copy, or reflection revision history.

## Lifecycle and validation

The only transition is:

```text
DRAFT → COMPLETED
```

- A DRAFT may be created, edited, partially filled, or have any field cleared by its author.
- Completion requires all three text fields, after trimming whitespace, to be non-empty.
- Each field has a maximum of 2000 characters.
- A COMPLETED Reflection is immutable: it cannot be edited, cleared, returned to DRAFT, invalidated, skipped, or revised.

There are no `INVALIDATED`, `STALE`, `SKIPPED`, or history states.

## Eligibility and disclosure boundary

Reflection creation is permitted only when both conditions hold:

1. `Reflection.analysis_run.status == SUCCESS`.
2. A `StudentResultReveal` exists for the Run's Project and source draft:

```text
StudentResultReveal.project_id == analysis_run.project_id
StudentResultReveal.source_draft_version
    == analysis_run.model_revision.source_draft_version
```

The reveal's `first_analysis_run` need not equal `Reflection.analysis_run`. Once a source draft has been revealed, any SUCCESS Run for that Project and draft may own one Reflection. Reflection does not require Compare or Explain to have been opened; their teaching value is an application guidance, not a domain prerequisite.

## Authorization and Event lifecycle

Only the Project student owner may create a Reflection, edit a DRAFT, or complete it. Manager, Developer, and other users cannot author, modify, complete, or delete a student Reflection.

- DRAFT visibility: the student owner only.
- COMPLETED visibility: the student owner; assigned Manager and Developer may read through existing Project-read authorization, but remain read-only.
- Other users have no access.

ACTIVE permits eligible Reflection authoring. PURGED rejects it because raw Project operational data no longer exists. FINISHED_GRACE Reflection authoring is temporarily fail-closed. This narrow M4C safety rule does **not** resolve Master O-003, which remains open for the product's broader FINISHED_GRACE user-access policy.

P0 offers no manual student delete service or DELETE endpoint. DRAFT content can instead be edited or cleared; COMPLETED records remain immutable.

## HTTP boundary

Reflection is exposed only as an AnalysisRun-scoped singleton at `/projects/<project_id>/analyses/<run_id>/reflection/`, with an explicit `/complete/` action. Its route identity is the scoped Run, not a Reflection id. POST authoring creates the absent singleton or updates its DRAFT; missing fields preserve stored values and empty strings clear them. Read and authoring call the existing Reflection application services; Views never duplicate eligibility, lifecycle, event, ownership, or reveal policy. Reflection HTTP neither requires nor creates a new StudentResultReveal.

## Persistence, purge, and research boundary

Reflection persists only its three raw student inputs and the minimal learning-evidence metadata above. It does not snapshot or duplicate `comparison-v1`, `explanation-v1`, `result_json`, physical snapshots, solver input, Material, or Section data. Those facts remain traceable through `analysis_run`.

Raw Reflection text is Project operational learning evidence. Existing ordered Project/Event operational purge must delete it with the Project's other raw operational data. Long-term retention may contain only anonymous, de-identified, non-reconstructable derived research metrics or coding explicitly approved by research governance. Raw Reflection text is never retained permanently, including as a default "anonymized" archive.

## Non-evaluation and AI boundary

Reflection is not evaluation. M4C introduces no score, grade, ranking, pass/fail result, sentiment score, misconception classifier, "correct reflection" judgment, or automatic design recommendation.

M4C adds no LLM dependency. A future language-assistance feature may only assist expression; it cannot be mechanics, grading, or learning-evidence-truth authority, and requires its own design.

## M4C Gate 0A invariants

- Reflection is a Soft Gate.
- One AnalysisRun has at most one Reflection.
- `SUCCESS` plus same-source-draft `StudentResultReveal` is the only creation eligibility.
- DRAFT is editable and private; COMPLETED is immutable and staff-readable only under Project-read authorization.
- `next_iteration_intent` is P0 Design Rationale; no standalone rationale or iteration aggregate exists.
- No snapshots of result, Compare, or Explain are copied.
- Raw text is operational data and is deleted on purge.
- FINISHED_GRACE authoring fails closed without closing O-003.
- No manual delete, scoring, or AI evaluation is introduced.
