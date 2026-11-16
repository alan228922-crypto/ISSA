# M9 — Results Evidence & Teaching Loop Completion

## 0. Status, authority and delivery boundary

**OWNER SCOPE / IMPLEMENTATION PLAN / NATIVE SEQUENTIAL EXECUTION APPROVED — TEACHER / OWNER REVIEW PENDING**

Prepared and scope approved: 2026-10-21. M8 stable implementation baseline: `main@96c335dc1c1d742d4143817c02a51a0fc3961892`; **M8 CLOSED — STABLE ON MAIN**. M9 starting repository baseline: `main@619dd55fae7307027e449bfd67b99138d38d5d2e`, including the M9-PRE documentation synchronization. Later documentation-only changes are not M9 implementation.

The Owner approved this direction and the boundaries below for **CONTROLLED TEACHING / PILOT**, not unattended production deployment, then approved the [TDD implementation plan](../plans/2026-10-21-m9-results-teaching-loop.md), Native sequential Tasks 1–8, Task 2 checkpoint and one independent whole-branch review. Technical tasks and fresh gates are complete: **M9 IMPLEMENTED — TEACHER REVIEW PENDING**. Owner review remains PENDING. No merge, push, deployment or automatic manual environment is authorized. Original approved planning bytes remain preserved in `7edbc64`; current evidence is recorded separately.

Current authority is [MASTER_SPEC](../../specs/MASTER_SPEC.md), with [Workspace UX](../../specs/STUDENT_LEARNING_WORKSPACE_UX.md), [Comparison](../../specs/COMPARISON_CONTRACT.md), [Explanation](../../specs/EXPLANATION_CONTRACT.md), [Reflection](../../specs/REFLECTION_AND_RATIONALE_ARCHITECTURE.md), [Report](../../specs/CALCULATION_REPORT_ASSISTANCE_SPEC.md), and the approved post-M8 decision-status synchronization. This approved scope does not reopen D-M7-001/002/003 or D-M8-001/002/003/004. O-003 is RESOLVED; O-006 is RESOLVED — APPROVED SCOPE ONLY; O-004 is OPEN; O-001 is OPEN — MECHANICS REVIEW REQUIRED.

## 1. Problem and teaching goal

Students can build and analyze a truss, see force states and maximum displacement, and author Reflection. However, the current results presenter primarily retains Explain Level 1, member prediction comparison is more visible than displacement comparison, and professional values do not by themselves establish an understandable evidence-to-reflection task. Backend structured explanation already contains richer material; raw-dumping it is not an educational completion criterion.

The student should be able to answer:

1. Which members are in tension/compression under this analyzed model and load case?
2. Where is maximum displacement, including equally valid tied locations?
3. Where does my prediction agree or differ from the analysis evidence?
4. Which specific member/node/segment facts support what I say?
5. What would I choose to change or observe next?

Question 5 belongs to the student. The platform supplies evidence and prompts, not an answer or design recommendation. Demonstrating task completion is not proof of improved learning quality; Teacher/Owner review remains necessary.

## 2. Owner-approved exact scope

1. Present existing Explain Level 1/2/3 with a distinct student task at each level.
2. Complete maximum-displacement prediction comparison using actual candidate locations and magnitude.
3. Improve member prediction comparison and its supplied segment evidence.
4. Distinguish the student's representative force-path hypothesis from analysis facts.
5. Offer an explicit handoff from evidence to the same selected Run's existing Reflection.
6. Preserve MIXED, UNSURE, NOT_COMPARABLE and no-Prediction as valid non-scoring states.
7. Verify a real public-browser v2 teaching journey, including historical and authorization cases.

No additional feature is implied by the phrase "completion". Estimate: **M** for this bounded scope; a causal mechanics explanation engine, new history model, or A/B design comparison requires a separate decision and estimate.

## 3. Teaching loop and Soft Gates

```text
optional Prediction -> Analyze -> Results conclusion -> Evidence
-> Prediction comparison when available -> Explanation -> optional Reflection
```

This is guidance, not a new prerequisite state machine. Students may skip Prediction and Reflection. Opening evidence/comparison/explanation is not a domain prerequisite for Reflection; preserve its existing SUCCESS + same-source-draft reveal eligibility and authoring permissions. No new grade, score, ranking, automatic wrong-answer judgment, or learning-quality assessment.

## 4. Explicit Run authority and historical consistency

All selected teaching evidence belongs to one explicitly selected AnalysisRun and its immutable ModelRevision/snapshot. Never choose latest implicitly, replace it with current Draft data, use current collection order for historical labels, or pair another draft's Prediction with the selected Run. Repeated Runs for one revision remain distinct selections, not distinct design versions by assumption.

The source chain is:

```text
selected AnalysisRun -> linked Prediction (optional)
                    -> immutable ModelRevision / snapshot
                    -> authoritative result -> comparison / explanation
                    -> that Run's Reflection
```

All displayed member/node identities use the existing student-label authority with the selected snapshot. Stress, mass, material/section context and provenance likewise come from the selected Run's existing package, not current resource-library rows. Historical v1 readers and v2 Node provenance remain schema-dispatched; no real Project conversion or rewriting of old artifacts.

When the Draft later changes, show that the result is historical; do not display historical force evidence over current geometry as though it described the current Draft. Evidence focus must remain within a matching immutable context; if that cannot be represented safely, keep the historical evidence readable without misleading current-Canvas linkage. Never infer a mapping from coincident coordinates or a raw key shared by otherwise incompatible contexts.

Run switches clear obsolete derived presentation and must not allow late responses or pending Reflection text to be applied to another Run. Follow existing explicit-save rules; do not introduce autosave or auto-completion. These are presentation safeguards, not new historical revision semantics.

### Existing capability/readiness inspection

| Need | Existing source / contract | M9 boundary |
| --- | --- | --- |
| Explicit Project/Run lookup | `projects/urls.py`, `projects/views.py` scoped data/comparison/explanation/report routes | Reuse; no new selection authority |
| Frozen physical identity and engineering context | `analysis/reporting.py` geometry_connectivity / materials_sections / provenance and Run result | No current-Draft substitution |
| Optional prediction comparison | `learning/comparison.py`, comparison-v1 | Linked Prediction, exact source version; no cross-version pairing |
| Structured explanation | `learning/explanation.py`, explanation-v1 | Consume existing facts/templates; no mechanics recomputation |
| Run-scoped Reflection | `learning/urls.py`, `learning/services.py`, existing singleton | Preserve lifecycle, privacy and reveal gates |
| Selection/race handling | `projects/static/projects/workspace/run-context.js` | Reuse and protect explicit Run presentation |

Read-only inspection found these existing capabilities sufficient for the approved scope with **NO migration / NO new domain model** expected. Existing endpoint responses may expose necessary already-existing selected-Run/snapshot/Prediction/Explanation facts; this does not authorize newly persisted facts. This is not a completed browser acceptance claim. If safe Run binding cannot be achieved within that existing authority, **STOP — ARCHITECTURE DECISION REQUIRED**. Do not invent a history domain or schema to continue.

## 5. Progressive disclosure and safe provenance

| Level | Student task | Approved content |
| --- | --- | --- |
| 1 — Conclusion | What happened? | Main tension/compression states, maximum displacement, an available prediction comparison summary, and neutral pointers to evidence worth examining |
| 2 — Evidence / Explanation | What supports that statement? | Member and complete segment evidence, displacement candidate evidence, prediction-vs-result explanation, student's path hypothesis versus supplied force facts |
| 3 — Professional data / provenance | Which values and analyzed source? | True numerical values/units, member/segment source, selected analyzed-model context and readable Run identity |

"Main" / "worth examining" must not create a new ranking threshold, safety verdict or recommendation. Reuse supplied classifications and evidence; display complete facts on request. Backend template levels are not UI screens by default: compose understandable, labeled tasks rather than expose raw JSON or concatenate all text. Engineering tables must not return to the first screen.

Preserve the prior internal-disclosure boundary at **all three levels**: no raw machine codes, client keys, DB row IDs, schema strings, hashes, raw payloads or internal mappings in student copy. Run identity/provenance means the existing human-readable analysis selection, historical context and stable student labels, not raw `analysis_run_id` or input_hash. Legitimate engineering values and units remain visible. Unknown errors use safe what-happened/why/next-action copy, not raw server messages. This is not a broader developer console or report-provenance redesign.

## 6. Member prediction comparison and Explain

Present the linked Prediction judgment beside the existing actual PhysicalMember teaching state and supplied segment evidence. Reuse backend O-007 classification; do not duplicate its threshold or reclassify forces in JavaScript. Keep real segment axial forces visible at the appropriate depth.

- MATCH / MISMATCH: "和预测一致 / 和预测不同", not correct/incorrect or pass/fail.
- UNSURE is a **student prediction choice**, not a Solver state or an error.
- ZERO_FORCE is the approved teaching classification, not mathematical proof of exact zero.
- MIXED preserves all differing segment facts; do not select the largest segment as the PhysicalMember truth.
- NOT_COMPARABLE remains the existing member comparison result for a determinate judgment versus MIXED; no penalty, score or forced binary verdict.

Explain must expose its existing Level 2 reasoning prompts and Level 3 supporting values as well as Level 1. It does not promise a newly computed causal proof, joint-equilibrium engine, counterfactual solver, or optimization advice. Preserve deterministic source facts and existing block semantics.

## 7. Maximum-displacement prediction comparison

Current prediction-v1 / prediction-v2 record a **location**, not a predicted numerical displacement magnitude. Therefore compare the predicted location with the actual maximum candidate set, and show the actual supplied magnitude in mm. Do not add a predicted-value field, fabricate a prediction value or percentage error, or alter the Prediction schema. A future numerical Prediction requires a new scope decision.

Use existing server-derived maximum magnitude, complete candidate set, tie policy and `location_match`; do not recalculate them in the browser. Match by immutable provenance, not nearest coordinates. All tied candidates remain visible; a prediction matching any supplied maximum candidate is handled by the existing contract, without choosing a single supposedly unique answer.

| Case | Required presentation |
| --- | --- |
| Linked prediction and valid result | Predicted location, actual candidate location(s), actual magnitude, and supplied agreement/difference explanation |
| Ties / multiple candidates, including zero-displacement ties | Preserve every valid candidate and the supplied match outcome; no arbitrary winner |
| No Prediction | Explicit neutral unavailable-comparison message; actual results and Explain remain usable |
| Member NOT_COMPARABLE | Preserve its member-level meaning; do not invent a displacement NOT_COMPARABLE enum |
| Missing/invalid result or inconsistent provenance | Safe unavailable/error state from existing contract; no zero substitution, latest fallback, coordinate guess or fabricated match |

## 8. Force-path hypothesis boundary

Always label the representative path as the **student's hypothesis**, with the associated supplied axial-force/state/segment evidence. Suitable prompt: "这些结果是否支持你的判断？" Never say the Solver calculated the unique true path, grade the path, generate an actual_load_path, or claim its mechanical correctness.

Without a linked Prediction, do not fabricate a path. Explain's existing no-Prediction member/displacement flow remains legal. UNSURE remains student uncertainty, not a numerical force classification.

## 9. Stress / mass and mechanics non-goals

Existing authoritative stress (`N/A`) and mass (`rho A L`) may support the selected Run's engineering evidence. Consume existing values; no second frontend mechanics engine. Neither value implies material-strength acceptance, structural safety, optimization, or buckling screening. Mass does not imply that self-weight loads were applied.

Keep Solver / postprocess / numerical result contracts, units mm/N/MPa/g, Node-as-Joint, Draft Independence, Delete Impact, validation and immutable history unchanged. No new force classification thresholds, stiffness calculation, axial-force recovery or support assumptions.

Explicitly excluded: Euler critical loads/ratios, stability risk bands, K recommendation and controlling-axis inference. O-001 remains OPEN — MECHANICS REVIEW REQUIRED. "该构件主要受压" is permitted; "该构件有屈曲危险" is not an authorized deterministic conclusion. Existing explicit-input Euler helper does not authorize screening.

## 10. Reflection handoff and permissions

From selected evidence, a student may navigate to the **same selected Run's** existing Reflection. Navigation itself does not save, auto-fill, complete or grade anything. Existing student-only authoring, three prompts, partial DRAFT save, explicit completion and COMPLETED immutability remain unchanged. Student answers are original reasoning, unexpected results and next_iteration_intent; no generated answer or new evidence-text storage.

Preserve permissions: readonly Manager/Developer never gain authoring or private DRAFT/Reasoning access; completed Reflection remains readable only through existing authorization. FINISHED_GRACE permits authorized historical Results/Report/Reflection reads but no student authoring/create/Save/Check/Analyze. PURGED operational GET/write fails closed, including residual rows. Do not change permission services as an incidental UX action.

## 11. Research and other non-goals

No large-scale tracking, surveillance, behavior score, AI reasoning score, student ranking, new research platform, or permanent raw free-text retention. Existing Reflection text remains operational data subject to purge. Anonymous derived metrics, research coding or longer retention require separate research-governance approval. No claims of demonstrated learning gains based only on UI completion.

Other exclusions: A/B design-version comparison, CompareRuns, DesignIteration, automatic design recommendations/optimization, AI-generated Reflection/grading, new Solver/Frame/3D, account lifecycle changes, Event admin expansion/Manager assignment, scheduler, Report export and new learning/history aggregates. O-004 remains OPEN; Event lifecycle gaps are not promoted into this controlled-pilot M9.

## 12. Approved acceptance obligations for later implementation

1. Real public UI on physical-draft-v2: ordinary student completes optional Prediction -> normal Analyze -> conclusion -> member/displacement evidence -> prediction comparison -> Explain -> self-authored Reflection save/complete. Relevant teaching evidence is asserted, not merely non-empty containers or visible tabs.
2. The public journey uses actual endpoint responses and normal persistence; no mock transport, direct JS controller/renderer invocation, fake result, or precreated AnalysisRun substitutes for the end-to-end proof. Synthetic setup may supply authorized users/Event/empty Project/catalog; modeling and the learning actions remain real public controls.
3. Separate legal no-Prediction path still reaches Results, Explain and optional Reflection, without a fake comparison or path.
4. Preserve and verify ties/multiple displacement candidates, UNSURE, ZERO_FORCE, MIXED and member NOT_COMPARABLE; distinguish missing result from a legal no-Prediction state. Focused tests may isolate edge cases, but do not replace criterion 1.
5. Historical Run A -> changed Draft / Run B -> select A: A's frozen values, labels, linked Prediction comparison and Reflection remain A's; no latest fallback, current-Draft overlay substitution, cross-Run writes or late-response contamination. Keep legacy v1 history readable without converting it.
6. Readonly viewer, GRACE and PURGED checks preserve the existing role, lifecycle, privacy and fail-closed rules. Navigation to Reflection causes no authoring mutation.
7. All three levels have the specified student task and relevant evidence; no raw dump, internal identifier disclosure, unique true path, safety verdict, score or auto-generated answer. Existing units/classifications/numerical values are preserved.
8. Owner/Teacher manually inspect whether a beginner can locate evidence and explain their own next observation. Browser GREEN is not substituted for Owner product acceptance or a research learning-effect finding.

These are future acceptance obligations, not tests implemented or run by this planning step. The implementation plan must specify genuine RED -> minimal implementation -> targeted/public-browser/regression gates. No new tests or migrations are created in this documentation step.

## 13. Remaining review decisions and stop conditions

Owner scope approval is recorded above. The next gate is Owner approval of the TDD implementation plan and execution method; scope approval alone does not start implementation. No M7/M8 policy is reopened.

**TEACHING REVIEW GATE is required before final Owner product acceptance**, not before planning against existing approved mechanics facts. Teacher review items:

- Confirm that the five student questions in §1 and evidence tasks in §5 are the minimum useful controlled-pilot activity.
- Review Explanation Level 1/2/3 depth and order.
- Review the amount of member-segment and displacement-candidate evidence for beginners.
- Review UNSURE / MIXED / tie wording for misleading certainty.
- Confirm manual product tasks that demonstrate students can cite evidence and choose their own next observation, without grading, safety interpretation or claiming measured learning improvement.

O-001 K/I/L/risk decisions are not prerequisites for this scope and must not be silently resolved by review of these prompts. Existing Report teacher-review items are not closed by this approval. Teacher feedback confined to wording, ordering and disclosure depth permits bounded UX revision; new mechanics interpretation, K/I/L, safety, force-path authority or classification requires **STOP — MECHANICS / SCOPE DECISION REQUIRED**.

If safe Run binding needs newly persisted facts, a new history domain/schema, or assumptions beyond the allowed existing-endpoint projections, STOP for **ARCHITECTURE DECISION REQUIRED**; do not expand the scope to continue. Owner plan/method approval now permits the bounded implementation; actual technical and human gate outcomes belong to the implementation/review evidence, never an inferred acceptance claim.
