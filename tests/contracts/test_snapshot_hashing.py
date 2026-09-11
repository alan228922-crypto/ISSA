from analysis.hashing import model_hash

def test_canonical_hash_ignores_dict_key_order_and_changes_with_value():
    first={'schema_version':'physical-snapshot-v1','nodes':[{'id':'a','x_mm':0.333333333333}]}
    same={'nodes':[{'x_mm':0.333333333333,'id':'a'}],'schema_version':'physical-snapshot-v1'}
    changed={'schema_version':'physical-snapshot-v1','nodes':[{'id':'a','x_mm':0.333333333334}]}
    assert model_hash(first)==model_hash(same)
    assert model_hash(first)!=model_hash(changed)
