from pathlib import Path

def test_idealization_has_no_django_or_orm_imports():
    source=Path('idealization/truss2d.py').read_text()
    assert 'django' not in source
    assert '.models import' not in source
