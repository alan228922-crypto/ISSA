# Draft Object Independence — design

## Intent and authority

Students may edit and delete any object in the current physical draft without deleting its dependents. The current draft may be incomplete; Model Check reports actionable gaps and Analyze refuses an incomplete draft before creating a snapshot, revision, run or invoking the solver. Historical revisions and mechanics units remain immutable. The frozen Product Owner decision D-DRAFT-INDEPENDENCE-01 is the authority.

## Existing domain audit

| Entity | Current links and deletion | Services / serialization / analysis |
| --- | --- | --- |
| GeometryNode | `project CASCADE`; referenced by Member start/end and Connection geometry via `CASCADE` | Whole-draft save deletes nodes then recreates graph; workspace/snapshot dereference nodes |
| PhysicalMember | `project CASCADE`; start/end `CASCADE NOT NULL`; Material/Section `PROTECT NOT NULL`; implicit Connection M2M | Save requires all refs; workspace and snapshot dereference them; idealizer consumes strict snapshot |
| Connection | `project CASCADE`; geometry node `CASCADE NOT NULL`; implicit participating-member M2M silently removes rows on member delete | Save sets participants; workspace serializes only extant members; snapshot and idealizer require complete relationships |
| Support | `project CASCADE`; target Connection `CASCADE NOT NULL` | Save and workspace require target; snapshot dereferences it |
| NodeLoad | `project CASCADE`; target Connection `CASCADE NOT NULL` | Save and workspace require target; snapshot dereferences it |
| Material | owner `CASCADE`; referenced by Member and Strip `PROTECT` | Owner catalog and form edit; no delete endpoint; snapshot freezes numeric material values |
| Section | owner `CASCADE`; referenced by Member `PROTECT` | Owner catalog and form edit; no delete endpoint; snapshot freezes numeric section values |
| Strip | owner `CASCADE`; Material `PROTECT NOT NULL` | Section definition may contain a `strip_id` JSON value; it is not an FK and is not rewritten |

Project purge is an ordered transaction that deletes historical operational entities first, then Support, NodeLoad, Connection, Member and Node. Its Project ownership CASCADE links remain unchanged. Snapshot and idealizer stay strict; no incomplete data enters them.

## Chosen design

Draft references that can be unresolved become nullable `SET_NULL`: Member start/end/Material/Section, Connection geometry node, Support/Load target Connection, Strip Material. Ownership FKs remain CASCADE. Existing implicit M2M becomes a `ConnectionParticipation` through model with one nullable `member` FK (`SET_NULL`) and a stable position per Connection. The through rows are the sole participation authority. A deleted member leaves a null slot; no ghost IDs or extra registry. Data migration copies existing M2M rows into slots before dropping the implicit table; each connection's members are sorted by client key to produce deterministic positions. New connections may still have zero slots; only a null slot means a known missing participant.

`physical-draft-v1` remains the wire schema. Nullable reference fields use JSON `null`; `participating_member_client_keys` permits null elements as participation slots. Non-null keys must resolve in the same project/owner and duplicates remain invalid. Save remains an atomic whole-draft replacement with optimistic `draft_version`; it recreates through slots including nulls. Workspace bootstrap round-trips them. The strict physical snapshot keeps its existing shape and is called only after completeness validation.

Material/Section delete is one owner-authorized domain service transaction. It locks affected Projects in deterministic ID order, counts affected Members/Strips, clears current references, increments each affected Project's `draft_version` once, deletes the resource, and writes a durable receipt with actor, resource identity, affected project IDs and object counts (but no historical payload). A Strip-only Material impact records its count but does not bump an unrelated Project. Save/analyze lock the same Project rows; a stale editor then receives the existing `STALE_DRAFT` response. The public delete route uses POST and a confirmation screen/impact preview; never GET mutation.

The material catalog lists retained Strips and labels a null material as “未指定”. An owner-scoped rebind form assigns another owned Material without recreating the Strip.

Model Check first scans current ORM draft for missing references and null participation slots. Each issue has stable code, severity, student-facing simplified Chinese text and an exact `physical_object` target. It returns those issues without snapshot or solver. Analyze calls the same preflight under Project lock and raises a typed validation error before revision creation. Complete drafts proceed through existing strict snapshot, idealizer and mechanics paths unchanged.

The editor's atomic delete clears surviving references to null while removing only selected objects, preserving slot positions. Undo's existing immutable draft history restores identities and references. Properties provide controls for every nullable relation and an object list for objects no longer drawable on the canvas. Delete confirmation explains counts of objects that will need rebind, then executes through the same action for keyboard and button. Incomplete objects remain in the object list and are labeled “未指定”; geometric rendering skips only shapes without a position. They do not vanish from the editable draft.

## Migration and validation

Migration alters only current editable models and adds participation slots and resource-delete audit. It copies old M2M rows before removing the old relationship/table. No historical table or solver code changes. RED tests cover direct ORM deletion, service/resource deletion across projects, save/reload/rebind, model-check issues, analyze preflight, history immutability, editor undo and browser controls. Then targeted tests, nonbrowser suite, browser suite, Django checks, migration check, and diff check run.

Rolling this migration back is permitted for complete participation rows, but explicitly refused if a current draft contains a null participation slot: the legacy M2M cannot represent that gap without silent data loss.

## Risks / invariants

- A complete draft must serialize to the same canonical snapshot as before.
- A missing participant slot is distinct from an intentionally empty participation list.
- Null can be saved; a stale non-null reference cannot be invented by the client.
- Cross-project resource deletion has no partial result or double version increments.
- Historical revisions never point at current Material/Section records; their frozen values remain unchanged.
