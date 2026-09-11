from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError


@pytest.fixture
def owner(db):
    from accounts.models import User
    return User.objects.create_user('team1')


@pytest.mark.django_db
def test_material_and_strip_accept_valid_owner_scoped_engineering_values(owner):
    from materials.models import Material,Strip
    material=Material.objects.create(owner_user=owner,name='竹材',E_MPa=Decimal('2000'),density_g_per_mm3=Decimal('0.0007'),source_type='MEASURED')
    strip=Strip.objects.create(owner_user=owner,material=material,name='1x6',width_mm=1,thickness_mm=6)
    assert strip.material_id==material.id


@pytest.mark.django_db
@pytest.mark.parametrize('field,value',[('E_MPa',0),('E_MPa',-1),('density_g_per_mm3',-1)])
def test_material_rejects_invalid_engineering_values(owner,field,value):
    from materials.models import Material
    material=Material(owner_user=owner,name='竹材',E_MPa=100,density_g_per_mm3=0,source_type='MEASURED')
    setattr(material,field,value)
    with pytest.raises(ValidationError):
        material.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize('value',[Decimal('NaN'),Decimal('Infinity')])
def test_material_rejects_nonfinite_engineering_values(owner,value):
    from materials.models import Material
    material=Material(owner_user=owner,name='竹材',E_MPa=value,density_g_per_mm3=0,source_type='MEASURED')
    with pytest.raises(ValidationError):
        material.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize('field,value',[('width_mm',0),('thickness_mm',0),('width_mm',-1)])
def test_strip_rejects_nonpositive_dimensions(owner,field,value):
    from materials.models import Material,Strip
    material=Material.objects.create(owner_user=owner,name='竹材',E_MPa=100,density_g_per_mm3=0,source_type='MEASURED')
    strip=Strip(owner_user=owner,material=material,name='条材',width_mm=1,thickness_mm=1)
    setattr(strip,field,value)
    with pytest.raises(ValidationError):
        strip.full_clean()


@pytest.mark.django_db
def test_strip_cannot_reference_another_users_material(owner):
    from accounts.models import User
    from materials.models import Material,Strip
    other=User.objects.create_user('team2')
    material=Material.objects.create(owner_user=other,name='竹材',E_MPa=100,density_g_per_mm3=0,source_type='MEASURED')
    strip=Strip(owner_user=owner,material=material,name='条材',width_mm=1,thickness_mm=1)
    with pytest.raises(ValidationError):
        strip.full_clean()
