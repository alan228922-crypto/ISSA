"""纯快照到 TrussModel；只有显式 Connection 才创建共享分析节点。"""
from dataclasses import dataclass
from math import hypot
from mechanics.truss2d.model import Member, Node, NodalLoad, Support, TrussModel

class IdealizationError(ValueError): pass
@dataclass(frozen=True)
class IdealizationResult:
    model: TrussModel
    analysis_node_to_physical: dict
    analysis_member_to_physical: dict
    physical_member_to_analysis: dict

def idealize(snapshot):
    if snapshot.get('schema_version')!='physical-snapshot-v1': raise IdealizationError('UNSUPPORTED_SNAPSHOT_SCHEMA')
    nodes={x['id']:x for x in snapshot['nodes']}; members=sorted(snapshot['physical_members'],key=lambda x:x['id'])
    connections={x['id']:x for x in snapshot['connections']}
    participation={m['id']:[] for m in members}
    for c in connections.values():
        for mid in c['participating_member_ids']: participation.setdefault(mid,[]).append(c)
    output_nodes=[]; output_members=[]; node_map={}; member_map={}; reverse={}
    def add_node(key,x,y,ref):
        if key not in node_map: output_nodes.append(Node(key,x,y)); node_map[key]=ref
        return key
    for m in members:
        a,b=nodes[m['start_node_id']],nodes[m['end_node_id']]; dx=b['x_mm']-a['x_mm']; dy=b['y_mm']-a['y_mm']; length=dx*dx+dy*dy
        points=[(0.0,'free:'+m['id']+':START',a),(1.0,'free:'+m['id']+':END',b)]
        for c in participation.get(m['id'],[]):
            p=nodes[c['geometry_node_id']]; cross=dx*(p['y_mm']-a['y_mm'])-dy*(p['x_mm']-a['x_mm']); t=((p['x_mm']-a['x_mm'])*dx+(p['y_mm']-a['y_mm'])*dy)/length
            if abs(cross)>1e-9*max(1.0,hypot(dx,dy)) or t < -1e-12 or t > 1+1e-12: raise IdealizationError('CONNECTION_OFF_MEMBER')
            t=max(0,min(1,t))
            if t <= 1e-12: points[0]=(0.0,'connection:'+c['id'],p)
            elif t >= 1-1e-12: points[1]=(1.0,'connection:'+c['id'],p)
            else: points.append((t,'connection:'+c['id'],p))
        points.sort(key=lambda x:(x[0],x[1]))
        if any(abs(points[i][0]-points[i-1][0])<=1e-12 for i in range(1,len(points))): raise IdealizationError('ZERO_LENGTH_ANALYSIS_SEGMENT')
        ids=[add_node(key,p['x_mm'],p['y_mm'],{'kind':'connection' if key.startswith('connection:') else 'free_endpoint','id':key}) for _,key,p in points]
        seg=[]
        for i,(left,right) in enumerate(zip(ids,ids[1:])):
            mid=m['id']+':'+str(i+1); output_members.append(Member(mid,left,right,m['material']['E_MPa'],m['section']['A_mm2'])); member_map[mid]=m['id']; seg.append(mid)
        reverse[m['id']]=seg
    supports=[]
    for s in snapshot['supports']:
        key='connection:'+s['connection_id']; supports.append(Support(key,s['support_type']=='PINNED' or s['restrained_axis']=='X',s['support_type']=='PINNED' or s['restrained_axis']=='Y'))
    loads=[]
    for l in snapshot['node_loads']: loads.append(NodalLoad('connection:'+l['connection_id'],l['fx_N'],l['fy_N']))
    return IdealizationResult(TrussModel('truss2d-input-v1',tuple(output_nodes),tuple(output_members),tuple(supports),tuple(loads)),node_map,member_map,reverse)
