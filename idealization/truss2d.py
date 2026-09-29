"""纯快照到 TrussModel；只有显式 Connection 才创建共享分析节点。"""
from dataclasses import dataclass
from math import hypot
from mechanics.truss2d.model import Member, Node, NodalLoad, Support, TrussModel


# 閱讀提示：這裡把學生畫出的結構，轉成 Solver 可以計算的節點和構件。

# PhysicalMember 是學生理解的完整構件；analysis member 是 Solver 實際計算的分段構件。
# 本檔案同時保留兩者的對應表，讓分析結果可以再顯示回學生原本看到的構件。

class IdealizationError(ValueError): pass
@dataclass(frozen=True)
class IdealizationResult:
    model: TrussModel
    analysis_node_to_physical: dict
    analysis_member_to_physical: dict
    physical_member_to_analysis: dict

def idealize(snapshot):
    if snapshot.get('schema_version') == 'physical-snapshot-v2':
        from .truss2d_v2 import idealize_v2

        return idealize_v2(snapshot)
    # ========================================================
    # 函數用途：把 physical-snapshot-v1 翻譯成 truss2d-input-v1。
    #
    # 輸入是學生設計模型的固定 Snapshot；輸出是 TrussModel 和三張對應表。
    # 程式會依照明確的 Connection 切分物理構件，建立 Solver 的分析節點和分析構件，
    # 再把支承與荷載放到對應的分析節點上。
    # 如果 Snapshot 格式不支援、連接點不在構件上，或切出零長度分段，會回報錯誤。
    # ========================================================
    # 一根物理構件如果中間有連接點，就在連接點切開，變成數根分析構件。
    if snapshot.get('schema_version')!='physical-snapshot-v1': raise IdealizationError('UNSUPPORTED_SNAPSHOT_SCHEMA')
    nodes={x['id']:x for x in snapshot['nodes']}; members=sorted(snapshot['physical_members'],key=lambda x:x['id'])
    connections={x['id']:x for x in snapshot['connections']}
    participation={m['id']:[] for m in members}
    # participation 先建立「連接點參與哪些物理構件」的查找表，
    # 之後處理每根構件時，才能快速找到需要切分的位置。
    for c in connections.values():
        for mid in c['participating_member_ids']: participation.setdefault(mid,[]).append(c)
    output_nodes=[]; output_members=[]; node_map={}; member_map={}; reverse={}
    def add_node(key,x,y,ref):
        if key not in node_map: output_nodes.append(Node(key,x,y)); node_map[key]=ref
        return key
    for m in members:
        # 先依照端點和連接點在構件上的位置排序，再建立連續的分析構件。
        a,b=nodes[m['start_node_id']],nodes[m['end_node_id']]; dx=b['x_mm']-a['x_mm']; dy=b['y_mm']-a['y_mm']; length=dx*dx+dy*dy
        points=[(0.0,'free:'+m['id']+':START',a),(1.0,'free:'+m['id']+':END',b)]
        for c in participation.get(m['id'],[]):
            # cross 和 t 分別檢查連接點是否在構件線段上，以及它位於構件長度的哪個位置。
            # 這是幾何資料轉換，不是 Solver 的受力計算；不符合時不能安全建立分析分段。
            p=nodes[c['geometry_node_id']]; cross=dx*(p['y_mm']-a['y_mm'])-dy*(p['x_mm']-a['x_mm']); t=((p['x_mm']-a['x_mm'])*dx+(p['y_mm']-a['y_mm'])*dy)/length
            if abs(cross)>1e-9*max(1.0,hypot(dx,dy)) or t < -1e-12 or t > 1+1e-12: raise IdealizationError('CONNECTION_OFF_MEMBER')
            t=max(0,min(1,t))
            if t <= 1e-12: points[0]=(0.0,'connection:'+c['id'],p)
            elif t >= 1-1e-12: points[1]=(1.0,'connection:'+c['id'],p)
            else: points.append((t,'connection:'+c['id'],p))
        points.sort(key=lambda x:(x[0],x[1]))
        # 相同位置的點會造成零長度分析構件；這種模型無法提供有效的剛度，因此直接回報問題。
        if any(abs(points[i][0]-points[i-1][0])<=1e-12 for i in range(1,len(points))): raise IdealizationError('ZERO_LENGTH_ANALYSIS_SEGMENT')
        ids=[add_node(key,p['x_mm'],p['y_mm'],{'kind':'connection' if key.startswith('connection:') else 'free_endpoint','id':key}) for _,key,p in points]
        seg=[]
        for i,(left,right) in enumerate(zip(ids,ids[1:])):
            mid=m['id']+':'+str(i+1); output_members.append(Member(mid,left,right,m['material']['E_MPa'],m['section']['A_mm2'])); member_map[mid]=m['id']; seg.append(mid)
        reverse[m['id']]=seg
    supports=[]
    # Solver 只需要知道每個分析節點的 x/y 位移是否被固定；這裡把 UI 的支承類型轉成兩個布林值。
    # 支承和荷載只能放在明確的 Connection 上；沒有連接的自由端不會自動變成共用節點。
    for s in snapshot['supports']:
        key='connection:'+s['connection_id']; supports.append(Support(key,s['support_type']=='PINNED' or s['restrained_axis']=='X',s['support_type']=='PINNED' or s['restrained_axis']=='Y'))
    loads=[]
    # 節點荷載同樣從 Connection 對應到 analysis node，保留原本的 fx_N / fy_N 單位為牛頓。
    for l in snapshot['node_loads']: loads.append(NodalLoad('connection:'+l['connection_id'],l['fx_N'],l['fy_N']))
    return IdealizationResult(TrussModel('truss2d-input-v1',tuple(output_nodes),tuple(output_members),tuple(supports),tuple(loads)),node_map,member_map,reverse)
