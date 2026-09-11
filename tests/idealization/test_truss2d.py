import pytest
from idealization.truss2d import IdealizationError, idealize

def snap(connections=[]):
 return {'schema_version':'physical-snapshot-v1','nodes':[{'id':'a','x_mm':0.,'y_mm':0.},{'id':'b','x_mm':10.,'y_mm':0.},{'id':'c','x_mm':5.,'y_mm':0.}], 'physical_members':[{'id':'m','start_node_id':'a','end_node_id':'b','material':{'E_MPa':100.},'section':{'A_mm2':2.}}],'connections':connections,'supports':[],'node_loads':[]}

def test_mid_member_connection_splits_and_maps_deterministically():
 s=snap([{'id':'j','geometry_node_id':'c','participating_member_ids':['m']}]); r=idealize(s)
 assert [m.id for m in r.model.members]==['m:1','m:2']; assert r.physical_member_to_analysis['m']==['m:1','m:2']

def test_same_coordinate_without_connection_remains_free_endpoint():
 r=idealize(snap()); assert len(r.model.nodes)==2; assert all(v['kind']=='free_endpoint' for v in r.analysis_node_to_physical.values())

def test_off_member_connection_rejected():
 s=snap([{'id':'j','geometry_node_id':'c','participating_member_ids':['m']}]); s['nodes'][2]['y_mm']=1
 with pytest.raises(IdealizationError,match='CONNECTION_OFF_MEMBER'): idealize(s)
