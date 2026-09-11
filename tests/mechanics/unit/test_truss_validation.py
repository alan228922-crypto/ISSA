"""輸入驗證必須在矩陣運算前報告可定位的機器代碼，不依賴 UI 文案。"""
from dataclasses import replace, FrozenInstanceError
import pytest


def get_api():
    from mechanics.truss2d.model import TrussModel, Node, Member, Support, NodalLoad
    from mechanics.truss2d.validation import validate_truss_model
    return TrussModel, Node, Member, Support, NodalLoad, validate_truss_model


def make_bar(api):
    T,N,M,S,L,_ = api
    return T('truss2d-input-v1', (N('A',0,0),N('B',1000,0)),
             (M('AB','A','B',200000,100),), (S('A',True,True),S('B',False,True)),
             (L('B',100,0),))


def test_valid_model_is_immutable_and_validation_deterministic():
    api = get_api()
    bar = make_bar(api)
    *_,validate = api
    assert validate(bar) == ()
    assert validate(bar) == validate(bar)
    with pytest.raises(FrozenInstanceError):
        bar.nodes[0].x_mm = 1
    original = list(bar.nodes)
    copied = replace(bar,nodes=original)
    original.clear()
    assert len(copied.nodes) == 2


@pytest.mark.parametrize('case,code', [
 ('empty','EMPTY_MODEL'),('unknown_member','UNKNOWN_NODE_REFERENCE'),
 ('unknown_support','UNKNOWN_NODE_REFERENCE'),('unknown_load','UNKNOWN_NODE_REFERENCE'),
 ('node_id','DUPLICATE_NODE_ID'),('member_id','DUPLICATE_MEMBER_ID'),
 ('zero','ZERO_LENGTH_MEMBER'),('near_zero','ZERO_LENGTH_MEMBER'),
 ('pair','DUPLICATE_ANALYSIS_MEMBER'),('no_support','NO_SUPPORT'),
 ('insufficient','INSUFFICIENT_RESTRAINT'),('isolated','ISOLATED_NODE'),
 ('disconnected','DISCONNECTED_STRUCTURE'),('no_flags','INVALID_SUPPORT'),
 ('flag_type','INVALID_SUPPORT'),('schema','UNSUPPORTED_SCHEMA_VERSION')])
def test_invalid_topology(case,code):
    api = get_api()
    bar = make_bar(api)
    T,N,M,S,L,validate = api
    changes = {
      'empty':dict(nodes=(),members=()),
      'unknown_member':dict(members=(replace(bar.members[0],node_j='C'),)),
      'unknown_support':dict(supports=(S('C',True,True),)),
      'unknown_load':dict(nodal_loads=(L('C',1,0),)),
      'node_id':dict(nodes=bar.nodes+(N('A',2,3),)),
      'member_id':dict(members=bar.members+bar.members),
      'zero':dict(nodes=(N('A',0,0),N('B',0,0))),
      'near_zero':dict(nodes=(N('A',0,0),N('B',1e-12,0))),
      'pair':dict(members=bar.members+(M('BA','B','A',200000,100),)),
      'no_support':dict(supports=()),
      'insufficient':dict(supports=(S('A',True,True),)),
      'isolated':dict(nodes=bar.nodes+(N('C',0,10),)),
      'disconnected':dict(nodes=bar.nodes+(N('C',0,10),N('D',1000,10)),
                           members=bar.members+(M('CD','C','D',200000,100),)),
      'no_flags':dict(supports=(S('A',False,False),)),
      'flag_type':dict(supports=(S('A',1,True),)),
      'schema':dict(schema_version='unknown-v2')}
    issues = validate(replace(bar,**changes[case]))
    assert code in {i.code for i in issues}
    assert all(i.severity in ('ERROR','WARNING') and i.entity_type for i in issues)


@pytest.mark.parametrize('field,code',[('E_MPa','INVALID_YOUNGS_MODULUS'),('A_mm2','INVALID_AREA')])
@pytest.mark.parametrize('value',[0,-1,float('nan'),float('inf'),True,'10'])
def test_invalid_member_parameters(field,code,value):
    api = get_api()
    bar = make_bar(api)
    issues=api[-1](replace(bar,members=(replace(bar.members[0],**{field:value}),)))
    issue=next(i for i in issues if i.code==code)
    assert issue.entity_ids == ('AB',) and issue.field == field


@pytest.mark.parametrize('value',[float('nan'),float('inf'),True,'10'])
def test_nonfinite_coordinate_and_load(value):
    api = get_api()
    bar = make_bar(api)
    *_,validate=api
    for candidate in (replace(bar,nodes=(replace(bar.nodes[0],x_mm=value),bar.nodes[1])),
                      replace(bar,nodal_loads=(replace(bar.nodal_loads[0],fy_N=value),))):
        assert 'INVALID_NUMERIC_VALUE' in {i.code for i in validate(candidate)}


def test_duplicate_supports_normalize_without_false_instability():
    api = get_api()
    bar = make_bar(api)
    T,N,M,S,L,validate=api
    assert validate(replace(bar,supports=(S('A',True,False),S('A',False,True),S('B',False,True)))) == ()


def test_orm_like_objects_are_not_solver_nodes():
    api = get_api()
    bar = make_bar(api)
    with pytest.raises(TypeError,match='Node'):
        replace(bar,nodes=(object(),))


@pytest.mark.parametrize('target,code',[('E_MPa','INVALID_YOUNGS_MODULUS'),('A_mm2','INVALID_AREA'),
                                       ('coordinate','INVALID_NUMERIC_VALUE'),('load','INVALID_NUMERIC_VALUE')])
def test_unrepresentable_integer_is_machine_readable(target,code):
    api=get_api()
    model=make_bar(api)
    huge=10**400
    if target=='coordinate':
        model=replace(model,nodes=(replace(model.nodes[0],x_mm=huge),model.nodes[1]))
    elif target=='load':
        model=replace(model,nodal_loads=(replace(model.nodal_loads[0],fx_N=huge),))
    else:
        model=replace(model,members=(replace(model.members[0],**{target:huge}),))
    assert code in {i.code for i in api[-1](model)}
