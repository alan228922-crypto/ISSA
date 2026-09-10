"""先查契約與拓樸，再檢查明顯剛體自由度；真正機構仍須由求解階段檢查。"""
from math import hypot, isfinite
from numbers import Real
import numpy as np
from .model import TrussModel
from .errors import ValidationIssue

# mm 單位下的最小可接受長度；不以畫面像素或 benchmark 容差決定。
LENGTH_ATOL_MM = 1e-9


def _finite(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


def validate_truss_model(model: TrussModel) -> tuple[ValidationIssue, ...]:
    """回傳 deterministic issues；重複桿件拒絕，重複支承以 DOF 聯集解讀。"""
    issues: list[ValidationIssue] = []
    def add(code: str, kind: str = 'model', ids: tuple[str,...] = (), field: str | None = None) -> None:
        issues.append(ValidationIssue(code, 'ERROR', kind, ids, field))
    if model.schema_version != 'truss2d-input-v1':
        add('UNSUPPORTED_SCHEMA_VERSION')
    if not model.nodes or not model.members:
        add('EMPTY_MODEL')
    for kind, entities in (('node', model.nodes), ('member', model.members)):
        seen: set[str] = set()
        for entity in entities:
            if not isinstance(entity.id,str) or not entity.id:
                add('INVALID_IDENTIFIER',kind,field='id')
            elif entity.id in seen:
                add('DUPLICATE_NODE_ID' if kind=='node' else 'DUPLICATE_MEMBER_ID',kind,(entity.id,))
            else:
                seen.add(entity.id)
    # 不在不合法 ID 上做 dict/set 操作，避免 validation 自己崩潰。
    if any(i.code=='INVALID_IDENTIFIER' for i in issues):
        return tuple(issues)
    nodes = {n.id:n for n in model.nodes}
    valid_coordinates = True
    for node in model.nodes:
        for field in ('x_mm','y_mm'):
            if not _finite(getattr(node,field)):
                add('INVALID_NUMERIC_VALUE','node',(node.id,),field)
                valid_coordinates = False
    adjacency = {key:set() for key in nodes}
    pairs: set[tuple[str,...]] = set()
    for member in model.members:
        for field,code in (('E_MPa','INVALID_YOUNGS_MODULUS'),('A_mm2','INVALID_AREA')):
            value = getattr(member,field)
            if not _finite(value) or value <= 0:
                add(code,'member',(member.id,),field)
        if any(not isinstance(ref,str) or ref not in nodes for ref in (member.node_i,member.node_j)):
            add('UNKNOWN_NODE_REFERENCE','member',(member.id,))
            continue
        pair = tuple(sorted((member.node_i,member.node_j)))
        if pair in pairs:
            add('DUPLICATE_ANALYSIS_MEMBER','member',(member.id,))
        pairs.add(pair)
        adjacency[member.node_i].add(member.node_j)
        adjacency[member.node_j].add(member.node_i)
        if valid_coordinates:
            a,b=nodes[member.node_i],nodes[member.node_j]
            length = hypot(b.x_mm-a.x_mm,b.y_mm-a.y_mm)
            if not isfinite(length):
                add('INVALID_NUMERIC_VALUE','member',(member.id,),'length_mm')
            elif length <= LENGTH_ATOL_MM:
                add('ZERO_LENGTH_MEMBER','member',(member.id,))
    constraints: set[tuple[str,int]] = set()
    if not model.supports:
        add('NO_SUPPORT')
    for support in model.supports:
        if not isinstance(support.node_id,str) or support.node_id not in nodes:
            add('UNKNOWN_NODE_REFERENCE','support')
            continue
        flags=(support.restrain_ux,support.restrain_uy)
        if any(type(flag) is not bool for flag in flags) or not any(flags):
            add('INVALID_SUPPORT','support',(support.node_id,))
            continue
        constraints.update((support.node_id,dof) for dof,flag in enumerate(flags) if flag)
    for load in model.nodal_loads:
        if not isinstance(load.node_id,str) or load.node_id not in nodes:
            add('UNKNOWN_NODE_REFERENCE','load')
        for field in ('fx_N','fy_N'):
            if not _finite(getattr(load,field)):
                add('INVALID_NUMERIC_VALUE','load',field=field)
    if nodes:
        for key in sorted(adjacency):
            if not adjacency[key]:
                add('ISOLATED_NODE','node',(key,))
        visited: set[str] = set()
        pending=[next(iter(nodes))]
        while pending:
            key=pending.pop()
            if key not in visited:
                visited.add(key)
                pending.extend(adjacency[key]-visited)
        if len(visited)!=len(nodes):
            add('DISCONNECTED_STRUCTURE')
    if valid_coordinates and nodes and constraints:
        # 平面剛體運動有 tx、ty、轉動三個模式；約束在這三模式上的 rank 應為 3。
        # 座標先以首節點平移、再縮放，避免 mm 尺度影響 rank；這不是桿件機構判定。
        origin=next(iter(nodes.values()))
        offsets={key:(n.x_mm-origin.x_mm,n.y_mm-origin.y_mm) for key,n in nodes.items()}
        scale=max((abs(v) for xy in offsets.values() for v in xy),default=1.0) or 1.0
        if isfinite(scale):
            rows=[]
            for key,dof in sorted(constraints):
                x,y=offsets[key]
                rows.append((1,0,-y/scale) if dof==0 else (0,1,x/scale))
            if np.linalg.matrix_rank(np.array(rows,dtype=float)) < 3:
                add('INSUFFICIENT_RESTRAINT')
    return tuple(issues)
