from collections.abc import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings().database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)


def context(db: Session, *, user_id: str = "", institution_id: str = "") -> None:
    db.execute(
        text("SELECT set_config('app.user_id', :u, true), set_config('app.institution_id', :i, true)"),
        {"u": user_id, "i": institution_id},
    )


def database() -> Generator[Session, None, None]:
    with Session(engine) as db:
        try:
            with db.begin():
                yield db
        except BaseException:
            for path in db.info.get("uncommitted_files", []):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass  # Private orphan can be reconciled; never mask the transaction failure.
            raise
