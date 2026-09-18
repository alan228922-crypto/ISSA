"""分析编排只连接应用层与纯层；不实现刚度、求解或教学数学。"""
from math import hypot
from django.db import transaction
from django.utils import timezone
from analysis.hashing import canonical_json, model_hash
from analysis.models import AnalysisRun, SolverVersion, ValidationLog
from analysis.services import get_or_create_revision
from idealization.truss2d import IdealizationError, idealize
from mechanics.truss2d.solver import Truss2DSolver
from mechanics.truss2d.errors import MechanicsError
from mechanics.truss2d.validation import validate_truss_model
from mechanics.truss2d.postprocess import member_mass, member_stress, total_mass_g
from projects.services import can_modify_project

MESSAGES={'SINGULAR_GLOBAL_STIFFNESS':'模型目前无法得到唯一的位移解，可能存在整体移动或机构。请检查支座约束和杆件连接。','CONNECTION_OFF_MEMBER':'连接点不位于指定杆件上。请检查连接点位置和参与杆件。'}
class AnalysisError(ValueError):
    def __init__(self,code,status_code=400): super().__init__(code); self.code=code; self.status_code=status_code

def canonical_solver_input(model, mapping):
    return {'schema_version':model.schema_version,'nodes':sorted([{'id':x.id,'x_mm':x.x_mm,'y_mm':x.y_mm} for x in model.nodes],key=lambda x:x['id']),'members':sorted([{'id':x.id,'node_i':x.node_i,'node_j':x.node_j,'E_MPa':x.E_MPa,'A_mm2':x.A_mm2} for x in model.members],key=lambda x:x['id']),'supports':sorted([{'node_id':x.node_id,'restrain_ux':x.restrain_ux,'restrain_uy':x.restrain_uy} for x in model.supports],key=canonical_json),'loads':sorted([{'node_id':x.node_id,'fx_N':x.fx_N,'fy_N':x.fy_N} for x in model.nodal_loads],key=canonical_json),'physical_member_mapping':mapping}

def _solver_version():
    return SolverVersion.objects.get_or_create(solver_version=Truss2DSolver.version,defaults={'analysis_type':'TRUSS_2D','input_schema_version':'truss2d-input-v1','result_schema_version':'truss2d-result-v1'})[0]

def _result(model, solved, mapping, snapshot):
    forces={x.member_id:x.axial_force_N for x in solved.member_axial_forces}; nodes={x.id:x for x in model.nodes}; members={x.id:x for x in model.members}; physical={x['id']:x for x in snapshot['physical_members']}; results=[]; masses=[]
    for mid in sorted(members):
        member=members[mid]; pid=mapping[mid]; data=physical[pid]; stress=member_stress(mid,forces[mid],member.A_mm2); length=hypot(nodes[member.node_j].x_mm-nodes[member.node_i].x_mm,nodes[member.node_j].y_mm-nodes[member.node_i].y_mm); mass=member_mass(mid,data['material']['density_g_per_mm3'],member.A_mm2,length); masses.append(mass); results.append({'analysis_member_id':mid,'physical_member_id':pid,'axial_force_N':forces[mid],'axial_stress_MPa':stress.axial_stress_MPa,'state':stress.state,'mass_g':mass.mass_g,'buckling':None})
    return {'schema_version':'truss2d-result-v1','node_displacements':[{'analysis_node_id':x.node_id,'ux_mm':x.ux_mm,'uy_mm':x.uy_mm} for x in solved.node_displacements],'support_reactions':[{'analysis_node_id':x.node_id,'rx_N':x.rx_N,'ry_N':x.ry_N} for x in solved.support_reactions],'member_results':results,'total_mass_g':total_mass_g(masses),'diagnostics':solved.diagnostics.__dict__}

def analyze_project(*,project,actor,expected_draft_version,prediction_id=None,solver=None):
    if not can_modify_project(actor,project): raise AnalysisError('PROJECT_ANALYZE_DENIED',403)
    if expected_draft_version!=project.draft_version: raise AnalysisError('STALE_DRAFT',409)
    with transaction.atomic():
        # Draft saves take this same lock; eligibility and snapshot must see one draft.
        project=type(project).objects.select_for_update().get(pk=project.pk)
        if not can_modify_project(actor,project): raise AnalysisError('PROJECT_ANALYZE_DENIED',403)
        prediction=None
        if prediction_id is not None:
            from learning.models import Prediction
            try:
                prediction=Prediction.objects.filter(pk=prediction_id,project=project).first()
            except (TypeError,ValueError):
                prediction=None
            if prediction is None: raise AnalysisError('PREDICTION_NOT_FOUND',404)
            if prediction.status!=Prediction.Status.COMPLETED or prediction.created_by_id!=project.owner_user_id or prediction.prediction_schema_version!='prediction-v1': raise AnalysisError('PREDICTION_NOT_ELIGIBLE',409)
            if prediction.source_draft_version!=expected_draft_version or prediction.source_draft_version!=project.draft_version: raise AnalysisError('PREDICTION_STALE_DRAFT',409)
            from learning.services import PredictionError, discover_current_prediction
            try:
                current = discover_current_prediction(project)
            except PredictionError as exc:
                raise AnalysisError(exc.code, exc.status_code) from exc
            if current.get('state') != Prediction.Status.COMPLETED or current.get('prediction').id != prediction.id: raise AnalysisError('PREDICTION_NOT_ELIGIBLE',409)
        if expected_draft_version!=project.draft_version: raise AnalysisError('STALE_DRAFT',409)
        revision,_=get_or_create_revision(project=project,actor=actor)
    version=_solver_version(); run=None
    try:
        ideal=idealize(revision.physical_snapshot_json); input_json=canonical_solver_input(ideal.model,ideal.analysis_member_to_physical); run=AnalysisRun.objects.create(project=project,prediction=prediction,model_revision=revision,analysis_type='TRUSS_2D',solver_version=version,input_schema_version=ideal.model.schema_version,input_hash=model_hash(input_json),solver_input_json=input_json,created_by=actor)
        issues=validate_truss_model(ideal.model)
        if issues: raise MechanicsError(issues)
        solved=(solver or Truss2DSolver()).solve(ideal.model); run.result_schema_version='truss2d-result-v1'; run.result_json=_result(ideal.model,solved,ideal.analysis_member_to_physical,revision.physical_snapshot_json); run.diagnostics_json=solved.diagnostics.__dict__; run.status=AnalysisRun.Status.SUCCESS
    except (IdealizationError,MechanicsError) as exc:
        code=str(exc) if isinstance(exc,IdealizationError) else exc.issues[0].code; run.status=AnalysisRun.Status.VALIDATION_FAILED; run.failure_code=code; run.diagnostics_json={'stage':'IDEALIZATION_OR_MECHANICS','codes':[code]}
    except Exception as exc:
        run.status=AnalysisRun.Status.SOLVER_FAILED; run.failure_code='SOLVER_FAILED'; run.diagnostics_json={'stage':'SOLVER'}
    run.finished_at=timezone.now(); run.save();
    if run.status!=AnalysisRun.Status.SUCCESS: ValidationLog.objects.create(project=project,model_revision=revision,analysis_run=run,stage='ANALYSIS',code=run.failure_code,severity='ERROR',numeric_context=run.diagnostics_json)
    return run

def check_project(*,project,actor,expected_draft_version):
    if not can_modify_project(actor,project): raise AnalysisError('PROJECT_CHECK_DENIED',403)
    if expected_draft_version!=project.draft_version: raise AnalysisError('STALE_DRAFT',409)
    from modeling.snapshot import build_physical_snapshot
    try:
        model=idealize(build_physical_snapshot(project)).model; issues=validate_truss_model(model)
        if not issues:
            try: Truss2DSolver().solve(model)
            except MechanicsError as exc: issues=exc.issues
    except IdealizationError as exc: issues=[type('Issue',(),{'code':str(exc),'severity':'ERROR','entity_ids':()})()]
    return {'ok':not bool(issues),'draft_version':project.draft_version,'issues':[{'code':x.code,'severity':getattr(x,'severity','ERROR'),'stage':'MECHANICS','entity_refs':list(getattr(x,'entity_ids',())),'human_message':MESSAGES.get(x.code,'模型需要进一步检查。')} for x in issues]}
