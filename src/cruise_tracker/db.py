from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_Session = None


def get_engine(url: str | None = None):
    global _engine, _Session
    if _engine is None or url is not None:
        settings = get_settings()
        if url is None:
            settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url or settings.db_url, future=True)

        @event.listens_for(_engine, "connect")
        def _fk_on(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        _Session = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def init_db(url: str | None = None):
    from . import models  # noqa: F401  (register tables)

    engine = get_engine(url)
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope():
    get_engine()
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
