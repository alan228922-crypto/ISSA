"""Readonly numeric projection of one saved Run and its linked Revision.

No Solver, idealization, current Draft/catalog, teaching classification or writes.
Malformed saved facts fail closed at the shared graph or dependent layer boundary.
"""
from collections import Counter, defaultdict
from math import hypot, isfinite


_CAPABILITIES = ('geometry', 'loads', 'reactions', 'axial_forces', 'deformation')


class _Unavailable(ValueError):
    """Expected malformed/missing saved data, not a programmer exception."""


def _require(condition):
    if not condition:
        raise _Unavailable()


def _identity(value):
    _require(isinstance(value, str) and bool(value))
    return value


def _number(value):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool))
    try:
        valid = isfinite(value)
    except OverflowError:
        valid = False
    _require(valid)
    return value  # Do not round/coerce saved numerical facts.


def _saved_hash(value):
    if (isinstance(value, str) and len(value) == 64
            and all(character in '0123456789abcdefABCDEF' for character in value)):
        return value
    return None


def _rows(value):
    _require(isinstance(value, list) and all(isinstance(row, dict) for row in value))
    return value


def _index(value, key='id'):
    indexed = {}
    for row in _rows(value):
        identity = _identity(row.get(key))
        _require(identity not in indexed)
        indexed[identity] = row
    return dict(sorted(indexed.items()))


def _capability(ready, reason=None):
    return {'status': 'READY' if ready else 'UNAVAILABLE', 'reason': None if ready else reason}


def _layer(build, reason, *, missing=False):
    if missing:
        return None, _capability(False, reason.replace('INVALID_', 'MISSING_', 1))
    try:
        return build(), _capability(True)
    except _Unavailable:
        return None, _capability(False, reason)


def _geometry(run, snapshot):
    revision = run.model_revision
    _require(run.status == 'SUCCESS' and run.analysis_type == 'TRUSS_2D')
    _require(revision.project_id == run.project_id and revision.pk == run.model_revision_id)
    _require(isinstance(snapshot, dict))
    schema = snapshot.get('schema_version')
    _require(schema in ('physical-snapshot-v1', 'physical-snapshot-v2'))
    _require(schema == revision.physical_snapshot_schema_version)
    _require(snapshot.get('units') == {'length': 'mm', 'force': 'N', 'stress': 'MPa', 'mass': 'g'})
    source_nodes = _index(snapshot.get('nodes'))
    physical = _index(snapshot.get('physical_members'))
    for row in source_nodes.values():
        _number(row.get('x_mm')); _number(row.get('y_mm'))
    for row in physical.values():
        _require(_identity(row.get('start_node_id')) in source_nodes and _identity(row.get('end_node_id')) in source_nodes)
    graph = run.solver_input_json
    _require(isinstance(graph, dict) and graph.get('schema_version') == run.input_schema_version == 'truss2d-input-v1')
    nodes = _index(graph.get('nodes'))
    members = _index(graph.get('members'))
    _require(bool(nodes) and bool(members))
    mapping = graph.get('physical_member_mapping')
    _require(isinstance(mapping, dict) and set(mapping) == set(members))
    _require(all(isinstance(p, str) and p in physical for p in mapping.values()))

    # Enumerate exact known identities. Coordinates validate an identified source;
    # they never select a node, merge colocated nodes, or reconstruct topology.
    sources = {}
    allowed = {key: set() for key in physical}
    def source(key, kind, identity, node_key, endpoint=None):
        _require(key not in sources and _identity(node_key) in source_nodes)
        node = source_nodes[node_key]
        sources[key] = ({'kind': kind, 'identity': identity, 'endpoint': endpoint}, node['x_mm'], node['y_mm'])
    if schema.endswith('v2'):
        connections = {}
        for key in source_nodes:
            source('node:' + key, 'NODE', key, key)
        for key, row in physical.items():
            allowed[key].update(('node:' + row['start_node_id'], 'node:' + row['end_node_id']))
        pairs = set()
        for row in _rows(snapshot.get('member_joint_incidences')):
            member, node = row.get('member_id'), row.get('node_id')
            _require(isinstance(member, str) and isinstance(node, str))
            _require(member in physical and node in source_nodes and (member, node) not in pairs)
            pairs.add((member, node)); allowed[member].add('node:' + node)
    else:
        connections = _index(snapshot.get('connections'))
        for key, row in connections.items():
            source('connection:' + key, 'CONNECTION', key, row.get('geometry_node_id'))
            participants = row.get('participating_member_ids')
            _require(isinstance(participants, list) and all(isinstance(p, str) and p in physical for p in participants))
            _require(len(set(participants)) == len(participants))
            for member in participants:
                allowed[member].add('connection:' + key)
        for key, row in physical.items():
            for endpoint, field in [('START', 'start_node_id'), ('END', 'end_node_id')]:
                identity = 'free:' + key + ':' + endpoint
                source(identity, 'MEMBER_ENDPOINT', key, row[field], endpoint)
                allowed[key].add(identity)
    projected_nodes = []
    for key, row in nodes.items():
        _require(key in sources)
        ref, x, y = sources[key]
        _require(_number(row.get('x_mm')) == x and _number(row.get('y_mm')) == y)
        projected_nodes.append({'analysis_node_id': key, 'source_ref': ref,
                                'x_mm': x, 'y_mm': y, 'displacement': None,
                                'support_ids': [], 'load_ids': []})
    segments = []
    reverse = defaultdict(list)
    for key, row in members.items():
        first, last = row.get('node_i'), row.get('node_j')
        _require(isinstance(first, str) and isinstance(last, str))
        _require(first in nodes and last in nodes and first != last)
        try:
            length = hypot(nodes[last]['x_mm'] - nodes[first]['x_mm'], nodes[last]['y_mm'] - nodes[first]['y_mm'])
        except OverflowError:
            raise _Unavailable() from None
        _require(isfinite(length) and length > 0)
        parent = mapping[key]
        _require(first in allowed[parent] and last in allowed[parent])
        reverse[parent].append(key)
        segments.append({'analysis_segment_id': key, 'start_analysis_node_id': first,
                         'end_analysis_node_id': last, 'physical_member_id': parent,
                         'axial_force_N': None})
    labels = {
        'nodes': [{'id': key, 'label': row.get('label') if isinstance(row.get('label'), str) else '',
                   'x_mm': row['x_mm'], 'y_mm': row['y_mm']} for key, row in source_nodes.items()],
        'physical_members': [{'id': key, 'label': row.get('label') if isinstance(row.get('label'), str) else '',
                              'start_node_id': row['start_node_id'], 'end_node_id': row['end_node_id']} for key, row in physical.items()],
        'connections': [{'id': key, 'geometry_node_id': row['geometry_node_id']} for key, row in connections.items()],
        'supports': [], 'node_loads': [],
        'analysis_member_mapping': dict(sorted(reverse.items())),
    }
    return graph, nodes, projected_nodes, segments, labels


def _target(row, snapshot, nodes):
    if snapshot['schema_version'].endswith('v2'):
        key = 'node:' + _identity(row.get('node_id'))
    else:
        key = 'connection:' + _identity(row.get('connection_id'))
    _require(key in nodes)
    return key


def _supports(snapshot, graph, nodes):
    supports = []
    expected = defaultdict(lambda: [False, False])
    for key, row in _index(snapshot.get('supports')).items():
        node = _target(row, snapshot, nodes)
        kind, axis = row.get('support_type'), row.get('restrained_axis')
        _require((kind == 'PINNED' and axis is None) or (kind == 'ROLLER' and axis in ('X', 'Y')))
        for index, restrained in enumerate((kind == 'PINNED' or axis == 'X', kind == 'PINNED' or axis == 'Y')):
            expected[node][index] |= restrained
        supports.append({'support_id': key, 'analysis_node_id': node,
                         'support_type': kind, 'restrained_axis': axis})
    actual = defaultdict(lambda: [False, False])
    for row in _rows(graph.get('supports')):
        node = _identity(row.get('node_id'))
        _require(node in nodes)
        for index, field in enumerate(('restrain_ux', 'restrain_uy')):
            _require(isinstance(row.get(field), bool))
            actual[node][index] |= row[field]
    _require(dict(actual) == dict(expected))
    return supports


def _loads(snapshot, graph, nodes):
    loads = []
    for key, row in _index(snapshot.get('node_loads')).items():
        loads.append({'load_id': key, 'analysis_node_id': _target(row, snapshot, nodes),
                      'fx_N': _number(row.get('fx_N')), 'fy_N': _number(row.get('fy_N'))})
    actual = []
    for row in _rows(graph.get('loads')):
        node = _identity(row.get('node_id')); _require(node in nodes)
        actual.append((node, _number(row.get('fx_N')), _number(row.get('fy_N'))))
    expected = [(row['analysis_node_id'], row['fx_N'], row['fy_N']) for row in loads]
    _require(Counter(actual) == Counter(expected))
    return loads


def _displacements(result, nodes):
    indexed = _index(result.get('node_displacements'), 'analysis_node_id')
    _require(set(indexed) == set(nodes))
    return {key: {'ux_mm': _number(row.get('ux_mm')), 'uy_mm': _number(row.get('uy_mm'))} for key, row in indexed.items()}


def _reactions(result, supports):
    _require(supports is not None)
    related = defaultdict(list)
    for row in supports:
        related[row['analysis_node_id']].append(row['support_id'])
    indexed = _index(result.get('support_reactions'), 'analysis_node_id')
    _require(set(indexed) == set(related))
    return [{'analysis_node_id': key, 'rx_N': _number(row.get('rx_N')), 'ry_N': _number(row.get('ry_N')),
             'support_ids': sorted(related[key])} for key, row in indexed.items()]


def _forces(result, segments):
    indexed = _index(result.get('member_results'), 'analysis_member_id')
    _require(set(indexed) == {row['analysis_segment_id'] for row in segments})
    for segment in segments:
        _require(indexed[segment['analysis_segment_id']].get('physical_member_id') == segment['physical_member_id'])
    return {key: _number(row.get('axial_force_N')) for key, row in indexed.items()}


def build_visualization_projection(*, run):
    """Return deterministic factual data; callers authorize and load the Revision."""
    revision = run.model_revision
    provenance = {
        'project_id': run.project_id, 'analysis_run_id': run.pk,
        'model_revision_id': run.model_revision_id,
        'source_draft_version': revision.source_draft_version,
        'physical_snapshot_schema_version': revision.physical_snapshot_schema_version,
        'input_schema_version': run.input_schema_version,
        'result_schema_version': run.result_schema_version,
        'model_hash': _saved_hash(revision.model_hash), 'input_hash': _saved_hash(run.input_hash), 'readonly': True,
    }
    view = {'schema_version': 'analysis-visualization-v1', 'status': 'UNAVAILABLE',
            'provenance': provenance,
            'capabilities': {key: _capability(False, 'INVALID_SAVED_GEOMETRY') for key in _CAPABILITIES},
            'label_source': {'nodes': [], 'physical_members': [], 'connections': [],
                             'supports': [], 'node_loads': [], 'analysis_member_mapping': {}},
            'nodes': [], 'segments': [], 'supports': [], 'loads': [], 'reactions': []}
    if provenance['model_hash'] is None or provenance['input_hash'] is None:
        view['capabilities'] = {key: _capability(False, 'INVALID_SAVED_PROVENANCE') for key in _CAPABILITIES}
        return view
    snapshot = revision.physical_snapshot_json
    try:
        graph, node_index, nodes, segments, labels = _geometry(run, snapshot)
    except _Unavailable:
        return view
    result = run.result_json if isinstance(run.result_json, dict) else {}
    valid_result_schema = run.result_schema_version == result.get('schema_version') == 'truss2d-result-v1'
    if not valid_result_schema:
        result = {}
    supports, support_cap = _layer(lambda: _supports(snapshot, graph, node_index), 'INVALID_SAVED_SUPPORTS', missing=snapshot.get('supports') is None)
    loads, load_cap = _layer(lambda: _loads(snapshot, graph, node_index), 'INVALID_SAVED_LOADS', missing=snapshot.get('node_loads') is None or graph.get('loads') is None)
    displacements, displacement_cap = _layer(lambda: _displacements(result, node_index), 'INVALID_SAVED_DISPLACEMENTS', missing=result.get('node_displacements') is None)
    reactions, reaction_cap = _layer(lambda: _reactions(result, supports), 'INVALID_SAVED_REACTIONS', missing=result.get('support_reactions') is None)
    if support_cap['status'] != 'READY':
        reaction_cap = support_cap
    forces, force_cap = _layer(lambda: _forces(result, segments), 'INVALID_SAVED_AXIAL_FORCES', missing=result.get('member_results') is None)
    if not valid_result_schema:
        displacement_cap = reaction_cap = force_cap = _capability(False, 'UNSUPPORTED_SAVED_RESULT_SCHEMA')
    for row in nodes:
        key = row['analysis_node_id']
        if displacements is not None:
            row['displacement'] = displacements[key]
        row['support_ids'] = [s['support_id'] for s in supports or [] if s['analysis_node_id'] == key]
        row['load_ids'] = [l['load_id'] for l in loads or [] if l['analysis_node_id'] == key]
    if forces is not None:
        for row in segments:
            row['axial_force_N'] = forces[row['analysis_segment_id']]
    labels['supports'] = [{'id': s['support_id']} for s in supports or []]
    source_loads = {row['id']: row for row in snapshot.get('node_loads', [])} if loads is not None else {}
    labels['node_loads'] = [{'id': row['load_id'], 'label': source_loads[row['load_id']].get('label') if isinstance(source_loads[row['load_id']].get('label'), str) else ''} for row in loads or []]
    view.update(nodes=nodes, segments=segments, label_source=labels,
                supports=supports or [], loads=loads or [], reactions=reactions or [])
    view['capabilities'] = {'geometry': _capability(True), 'loads': load_cap,
                            'reactions': reaction_cap, 'axial_forces': force_cap,
                            'deformation': displacement_cap}
    view['status'] = 'READY' if all(c['status'] == 'READY' for c in view['capabilities'].values()) else 'PARTIAL'
    return view
