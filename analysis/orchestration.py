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


# ============================================================
# 檔案閱讀指南
#
# 這個檔案在系統中的角色：
# 它是「按下 Analyze 之後」的流程總管，負責把多個已存在的模組依序串起來。
#
# 它接收的主要資料：
# - Project：學生正在編輯的專案
# - actor：提出分析請求的使用者
# - expected_draft_version：呼叫端認為自己正在操作的草稿版本
# - prediction_id：可選的學生預測紀錄
#
# 它會呼叫的主要模組：
# - Revision / Snapshot：固定這次分析使用的模型版本
# - Idealizer：把物理模型轉成 Solver 模型
# - Mechanics validation / Solver：檢查並計算二維桁架
# - Post-process：把軸力整理成應力與質量
#
# 它最後產生：
# - AnalysisRun：這次分析的歷史紀錄
# - result_json 或 failure_code：成功結果或失敗原因
#
# 它負責流程控制與資料保存，但不負責剛度矩陣公式、數值求解公式或畫面顯示。
# ============================================================

# 閱讀提示：這個檔案是分析流程的總管，依序檢查權限、準備模型、執行 Solver，再保存結果。

MESSAGES={'SINGULAR_GLOBAL_STIFFNESS':'模型目前无法得到唯一的位移解，可能存在整体移动或机构。请检查支座约束和杆件连接。','CONNECTION_OFF_MEMBER':'连接点不位于指定杆件上。请检查连接点位置和参与杆件。'}

# 這裡把程式錯誤代碼整理成使用者看得懂的提示；底層仍保留穩定的錯誤代碼。
class AnalysisError(ValueError):
    # 這個例外把穩定的錯誤代碼和 HTTP 狀態碼一起帶回上層。
    # View 可以用 code 顯示對應提示，用 status_code 回傳合適的 HTTP 回應，
    # 不需要解析一大段例外文字來猜測發生什麼事。
    def __init__(self,code,status_code=400): super().__init__(code); self.code=code; self.status_code=status_code

def canonical_solver_input(model, mapping):
    # ========================================================
    # 函數用途：建立「可穩定比較」的 Solver 輸入資料。
    #
    # model 是 Idealizer 已經產生的 TrussModel，包含節點、分析構件、支承和荷載。
    # mapping 記錄 analysis member 如何對回學生原本的 physical member。
    #
    # 這裡不是重新計算力學，也不是改變模型；只是把資料整理成固定格式，
    # 讓後面產生的 input hash 能代表「內容」，而不是代表資料剛好被讀出的順序。
    # 欄位意義如下：
    # - schema_version：告訴讀取者這份輸入遵循哪一版資料格式。
    # - nodes：每個分析節點的 ID 和 x/y 座標，單位是 mm。
    # - members：分析構件的兩端節點、彈性模數 E（MPa）和面積 A（mm²）。
    # - supports：哪些分析節點的水平或垂直位移被固定。
    # - loads：作用在分析節點上的 fx / fy 外力，單位是 N。
    # - physical_member_mapping：分析構件如何對回學生原本看到的物理構件。
    # ========================================================
    # 先固定資料順序，再產生指紋，避免同一個模型因資料讀取順序不同而被當成不同模型。
    return {'schema_version':model.schema_version,'nodes':sorted([{'id':x.id,'x_mm':x.x_mm,'y_mm':x.y_mm} for x in model.nodes],key=lambda x:x['id']),'members':sorted([{'id':x.id,'node_i':x.node_i,'node_j':x.node_j,'E_MPa':x.E_MPa,'A_mm2':x.A_mm2} for x in model.members],key=lambda x:x['id']),'supports':sorted([{'node_id':x.node_id,'restrain_ux':x.restrain_ux,'restrain_uy':x.restrain_uy} for x in model.supports],key=canonical_json),'loads':sorted([{'node_id':x.node_id,'fx_N':x.fx_N,'fy_N':x.fy_N} for x in model.nodal_loads],key=canonical_json),'physical_member_mapping':mapping}

def _solver_version():
    # SolverVersion 是資料庫中的 Solver 版本紀錄。
    # 分析結果保存它，是為了讓日後查看歷史結果時知道當時使用哪一版計算程式，
    # 而不是把舊結果誤認為一定是目前版本重新計算的結果。
    # 保存 Solver 版本，讓日後查看舊結果時知道當時使用的是哪一版計算程式。
    return SolverVersion.objects.get_or_create(solver_version=Truss2DSolver.version,defaults={'analysis_type':'TRUSS_2D','input_schema_version':'truss2d-input-v1','result_schema_version':'truss2d-result-v1'})[0]

def _result(model, solved, mapping, snapshot):
    # ========================================================
    # 函數用途：把 Solver 的純數值結果整理成 API / 資料庫使用的結果格式。
    #
    # solved 已經包含節點位移、支承反力、構件軸力和診斷資料。
    # 這裡再補上學生介面需要的物理構件對應、應力、質量和總質量。
    #
    # 重要邊界：這裡是後處理，不會重新求解結構，也不會自行改寫 Solver 的軸力。
    # ========================================================
    # forces 讓後面可以用 analysis member id 快速找到 Solver 算出的軸力。
    # nodes / members 是分析模型的查找表；physical 是原始物理構件的查找表。
    # 這裡只整理 Solver 已算好的結果，不重新計算軸力，避免不同層得到不一致的答案。
    forces={x.member_id:x.axial_force_N for x in solved.member_axial_forces}; nodes={x.id:x for x in model.nodes}; members={x.id:x for x in model.members}; physical={x['id']:x for x in snapshot['physical_members']}; results=[]; masses=[]
    for mid in sorted(members):
        # ====================================================
        # 每一圈處理一根「分析構件」：
        # 1. 用 mapping 找回學生畫面上的 physical member。
        # 2. 使用 Solver 軸力和截面面積計算平均軸向應力。
        # 3. 用兩端節點座標計算長度，再估算理論質量。
        # 4. 將分析構件、物理構件、軸力、應力、狀態和質量放入結果。
        #
        # 一根 physical member 可能被 Idealizer 切成多根 analysis member，
        # 所以結果同時保留兩種 ID，才能在數學結果和學生畫面之間來回對應。
        # ====================================================
        member=members[mid]; pid=mapping[mid]; data=physical[pid]; stress=member_stress(mid,forces[mid],member.A_mm2); length=hypot(nodes[member.node_j].x_mm-nodes[member.node_i].x_mm,nodes[member.node_j].y_mm-nodes[member.node_i].y_mm); mass=member_mass(mid,data['material']['density_g_per_mm3'],member.A_mm2,length); masses.append(mass); results.append({'analysis_member_id':mid,'physical_member_id':pid,'axial_force_N':forces[mid],'axial_stress_MPa':stress.axial_stress_MPa,'state':stress.state,'mass_g':mass.mass_g,'buckling':None})
    # 每筆 member_results 都保留：分析構件 ID、物理構件 ID、軸力（N）、應力（MPa）、
    # 受拉／受壓狀態和質量（g）。這些資料讓前端能把數學結果顯示回學生的設計構件。
    # total_mass_g 只把每根 analysis member 的質量加總；node_displacements、
    # support_reactions 和 diagnostics 則直接保留 Solver 已經產生的資訊。
    # buckling 目前明確輸出 None，表示這個結果格式保留欄位，但本流程尚未提供屈曲結果。
    return {'schema_version':'truss2d-result-v1','node_displacements':[{'analysis_node_id':x.node_id,'ux_mm':x.ux_mm,'uy_mm':x.uy_mm} for x in solved.node_displacements],'support_reactions':[{'analysis_node_id':x.node_id,'rx_N':x.rx_N,'ry_N':x.ry_N} for x in solved.support_reactions],'member_results':results,'total_mass_g':total_mass_g(masses),'diagnostics':solved.diagnostics.__dict__}

def analyze_project(*,project,actor,expected_draft_version,prediction_id=None,solver=None):
    # ========================================================
    # 函數用途：完成一次正式 Project 分析。
    #
    # 白話理解：這就是使用者按下 Analyze 後，後端從權限檢查一路走到保存結果的總流程。
    #
    # 主要階段：
    # 1. 確認使用者能修改並分析這個 Project。
    # 2. 確認呼叫端手上的 draft version 仍是伺服器最新版本。
    # 3. 在資料庫交易中鎖定 Project，檢查可選的 Prediction，並取得 Revision。
    # 4. 將固定的 Physical Snapshot 理想化成 Solver Model。
    # 5. 建立 AnalysisRun，保存這次分析的輸入與 hash。
    # 6. 執行模型驗證和 Solver。
    # 7. 保存成功結果，或保存可追蹤的失敗狀態與 ValidationLog。
    #
    # 這個函數負責協調，不負責實作剛度矩陣或桁架求解公式。
    # ========================================================
    # 分析開始前要確認：使用者有權限，而且模型版本、分析快照與結果都屬於同一個專案。

    # ========================================================
    # 第 1 階段：在進入資料庫交易前做快速權限與版本檢查。
    # expected_draft_version 是呼叫端看到的版本；project.draft_version 是資料庫目前版本。
    # 兩者不同時，代表畫面上的模型可能已經過期，不能直接拿來分析。
    # ========================================================
    if not can_modify_project(actor,project): raise AnalysisError('PROJECT_ANALYZE_DENIED',403)
    if expected_draft_version!=project.draft_version: raise AnalysisError('STALE_DRAFT',409)
    with transaction.atomic():
        # ====================================================
        # 第 2 階段：在同一個資料庫交易中鎖定 Project。
        #
        # transaction.atomic() 讓這段資料庫操作要嘛一起成功，要嘛一起回復。
        # select_for_update() 鎖定 Project 資料列，避免同時保存草稿的請求在這段流程中
        # 改變分析正在使用的版本。這是資料一致性控制，不是 Solver 的數值運算鎖。
        # ====================================================
        # Draft saves take this same lock; eligibility and snapshot must see one draft.
        project=type(project).objects.select_for_update().get(pk=project.pk)
        # 鎖定後再次檢查權限，是因為等待鎖的期間其他資料可能已經改變；
        # 這裡以鎖內讀到的 Project 狀態作為真正進入分析的判斷依據。
        if not can_modify_project(actor,project): raise AnalysisError('PROJECT_ANALYZE_DENIED',403)
        prediction=None
        if prediction_id is not None:
            # ==================================================
            # 第 3 階段：如果有 Prediction，確認它能和這次分析配對。
            #
            # Prediction 是學生在看 Solver 結果前寫下的預測，因此不是 Solver 必要輸入。
            # 沒有 prediction_id 時可以直接分析；有 prediction_id 時，系統必須確認它屬於
            # 目前 Project、由專案擁有者建立、已完成、使用正確格式，且對應同一個 draft version。
            # 否則就可能拿舊模型的預測去比較新模型的分析結果。
            # ==================================================
            from learning.models import Prediction
            try:
                prediction=Prediction.objects.filter(pk=prediction_id,project=project).first()
            except (TypeError,ValueError):
                prediction=None
            if prediction is None: raise AnalysisError('PREDICTION_NOT_FOUND',404)
            if prediction.status!=Prediction.Status.COMPLETED or prediction.created_by_id!=project.owner_user_id or prediction.prediction_schema_version!='prediction-v1': raise AnalysisError('PREDICTION_NOT_ELIGIBLE',409)
            if prediction.source_draft_version!=expected_draft_version or prediction.source_draft_version!=project.draft_version: raise AnalysisError('PREDICTION_STALE_DRAFT',409)
        # 鎖定後再次比對版本，確保 Revision 不會建立在過期的草稿上。
            from learning.services import PredictionError, discover_current_prediction
            try:
                current = discover_current_prediction(project)
            except PredictionError as exc:
                raise AnalysisError(exc.code, exc.status_code) from exc
            if current.get('state') != Prediction.Status.COMPLETED or current.get('prediction').id != prediction.id: raise AnalysisError('PREDICTION_NOT_ELIGIBLE',409)
        if expected_draft_version!=project.draft_version: raise AnalysisError('STALE_DRAFT',409)
        # ====================================================
        # 第 4 階段：建立或重用 ModelRevision。
        #
        # Draft 是使用者目前可以繼續修改的資料；Revision 是這次正式分析要固定保存的版本。
        # get_or_create_revision() 會建立 Physical Snapshot、產生模型 hash，
        # 並在內容相同時重用既有 Revision。
        # ====================================================
        revision,_=get_or_create_revision(project=project,actor=actor)
    version=_solver_version(); run=None
    try:
        # ====================================================
        # 第 5 階段：Physical Snapshot → Solver Model → AnalysisRun。
        #
        # 下一行雖然把三件事寫在同一行，實際順序是：
        # 1. idealize() 把學生設計的物理模型轉成分析節點和分析構件。
        # 2. canonical_solver_input() 整理節點、構件、支承、荷載和 mapping。
        # 3. AnalysisRun.objects.create() 在資料庫建立這次正式分析的歷史紀錄。
        #
        # AnalysisRun 不是 Solver；它是「哪個模型版本用哪個 Solver 版本分析」的履歷，
        # 即使最後失敗，也能留下輸入 hash、模型版本和失敗階段。
        # ====================================================
        ideal=idealize(revision.physical_snapshot_json); input_json=canonical_solver_input(ideal.model,ideal.analysis_member_to_physical); run=AnalysisRun.objects.create(project=project,prediction=prediction,model_revision=revision,analysis_type='TRUSS_2D',solver_version=version,input_schema_version=ideal.model.schema_version,input_hash=model_hash(input_json),solver_input_json=input_json,created_by=actor)
        # ====================================================
        # 第 6 階段：先做模型驗證，再進入真正的結構求解。
        # validate_truss_model() 找出資料格式、拓樸或支承問題；有問題就不進 Solver。
        # MechanicsError 會把驗證問題帶回，稍後記為 VALIDATION_FAILED。
        # ====================================================
        issues=validate_truss_model(ideal.model)
        if issues: raise MechanicsError(issues)
        # ====================================================
        # 第 7 階段：執行 Solver 並整理成功結果。
        # Solver 產生位移、支承反力、構件軸力和診斷資料；_result() 再補上應力和質量。
        # SUCCESS 代表這次分析完成並有可保存的結果，不代表所有工程安全判斷都已完成。
        # ====================================================
        solved=(solver or Truss2DSolver()).solve(ideal.model); run.result_schema_version='truss2d-result-v1'; run.result_json=_result(ideal.model,solved,ideal.analysis_member_to_physical,revision.physical_snapshot_json); run.diagnostics_json=solved.diagnostics.__dict__; run.status=AnalysisRun.Status.SUCCESS
    except (IdealizationError,MechanicsError) as exc:
        # 理想化失敗或模型／力學驗證失敗，代表目前資料不能正常進入或完成分析；
        # 這類錯誤記為 VALIDATION_FAILED，讓前端知道應優先檢查模型，而不是重試同一計算。
        code=str(exc) if isinstance(exc,IdealizationError) else exc.issues[0].code; run.status=AnalysisRun.Status.VALIDATION_FAILED; run.failure_code=code; run.diagnostics_json={'stage':'IDEALIZATION_OR_MECHANICS','codes':[code]}
    except Exception as exc:
        # 其他未預期例外記為 SOLVER_FAILED；不把內部例外細節直接暴露給學生。
        # 具體原因仍保留在流程狀態與 diagnostics 的階段標記中，供後續維護追查。
        run.status=AnalysisRun.Status.SOLVER_FAILED; run.failure_code='SOLVER_FAILED'; run.diagnostics_json={'stage':'SOLVER'}
    # ========================================================
    # 第 8 階段：完成 AnalysisRun 並留下失敗紀錄。
    # finished_at 表示這次嘗試何時結束；失敗時另外建立 ValidationLog，
    # 把 Project、Revision、AnalysisRun、階段和錯誤代碼連在一起，方便後續分析常見問題。
    # ========================================================
    run.finished_at=timezone.now(); run.save();
    if run.status!=AnalysisRun.Status.SUCCESS: ValidationLog.objects.create(project=project,model_revision=revision,analysis_run=run,stage='ANALYSIS',code=run.failure_code,severity='ERROR',numeric_context=run.diagnostics_json)
    return run

def _check_issue_physical_object(entity_refs, snapshot, analysis_member_to_physical):
    """Only expose a canvas target when one solver reference has one exact physical identity."""
    if len(entity_refs) != 1:
        return None
    ref = entity_refs[0]
    member_id = analysis_member_to_physical.get(ref)
    if member_id is not None and member_id in {member['id'] for member in snapshot['physical_members']}:
        return {'kind': 'PHYSICAL_MEMBER', 'client_key': member_id}
    matches = [connection['id'] for connection in snapshot['connections'] if ref == f"connection:{connection['id']}"]
    if len(matches) == 1:
        return {'kind': 'CONNECTION', 'client_key': matches[0]}
    return None


def check_project(*,project,actor,expected_draft_version):
    # ========================================================
    # 函數用途：在不建立正式分析歷史的前提下，先檢查目前草稿能否進入分析。
    #
    # Check 會建立暫時的 Physical Snapshot，進行 Idealization、模型驗證，
    # 若驗證通過則實際呼叫 Solver 檢查是否能得到解；但不建立 Revision 或 AnalysisRun。
    # 回傳資料給前端後，前端可以先告訴學生要修正哪些問題，再決定是否正式 Analyze。
    # ========================================================
    # 模型檢查會走相同的轉換與求解檢查，但只回報問題，不保存正式分析紀錄。
    if not can_modify_project(actor,project): raise AnalysisError('PROJECT_CHECK_DENIED',403)
    if expected_draft_version!=project.draft_version: raise AnalysisError('STALE_DRAFT',409)
    from modeling.snapshot import build_physical_snapshot
    snapshot = build_physical_snapshot(project)
    mapping = {}
    try:
        # 這裡使用目前草稿的暫時 Snapshot；因為只是檢查，不把它保存成正式版本。
        idealization=idealize(snapshot); model=idealization.model; mapping=idealization.analysis_member_to_physical; issues=validate_truss_model(model)
        if not issues:
            # 驗證通過仍要試算，因為某些「沒有明顯格式問題」的模型可能仍沒有唯一解。
            try: Truss2DSolver().solve(model)
            except MechanicsError as exc: issues=exc.issues
    except IdealizationError as exc: issues=[type('Issue',(),{'code':str(exc),'severity':'ERROR','entity_ids':()})()]
    # 將內部 ValidationIssue 轉成前端可以直接顯示的資料：錯誤代碼、嚴重程度、
    # 關聯的節點或構件，以及不暴露內部例外的中文提示。
    return {'ok':not bool(issues),'draft_version':project.draft_version,'issues':[{'code':x.code,'severity':getattr(x,'severity','ERROR'),'stage':'MECHANICS','entity_refs':list(getattr(x,'entity_ids',())),'human_message':MESSAGES.get(x.code,'模型需要进一步检查。'), **({'physical_object': target} if (target := _check_issue_physical_object(tuple(getattr(x,'entity_ids',())), snapshot, mapping)) else {})} for x in issues]}
