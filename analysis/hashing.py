import hashlib
import json

def canonical_json(value):
    """哈希基于不展示四舍五入的权威快照值，拒绝 NaN/Infinity。"""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def model_hash(snapshot):
    return hashlib.sha256(canonical_json(snapshot).encode('utf-8')).hexdigest()
