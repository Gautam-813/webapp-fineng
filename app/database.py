from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()


def _engine_options() -> dict:
    options = {
        "echo": settings.debug,
        "pool_pre_ping": True,
    }
    if settings.database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        options["pool_size"] = 20
        options["max_overflow"] = 10
    return options


engine = create_engine(settings.database_url, **_engine_options())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> bool:
    if not settings.auto_create_tables:
        return False

    Base.metadata.create_all(bind=engine)
    return True
