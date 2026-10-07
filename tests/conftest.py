import pytest

from cruise_tracker import db
from cruise_tracker.config import get_settings


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    db.init_db(f"sqlite:///{tmp_path / 'test.db'}")
    from cruise_tracker.seed import seed_reference

    with db.session_scope() as s:
        seed_reference(s)
    with db.session_scope() as s:
        yield s
    get_settings.cache_clear()
