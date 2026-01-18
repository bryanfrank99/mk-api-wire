import contextvars
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

_current_user_id: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "current_user_id", default=None
)
_current_path: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_path", default=None
)


def set_audit_context(user_id: Optional[UUID], path: Optional[str]):
    token_user = _current_user_id.set(user_id)
    token_path = _current_path.set(path)
    return token_user, token_path


def reset_audit_context(token_user, token_path):
    _current_user_id.reset(token_user)
    _current_path.reset(token_path)


class DBAuditLogHandler(logging.Handler):
    """Write Python log records to the AuditLog table.

    This is intentionally simple: it stores application logs in the same place as
    provisioning/admin audit events so the Admin UI can show everything.
    """

    def __init__(self, engine, level=logging.INFO):
        super().__init__(level=level)
        self._engine = engine
        self._in_emit = False

    def emit(self, record: logging.LogRecord) -> None:
        if self._in_emit:
            return

        # Avoid extremely noisy / recursive loggers.
        if record.name.startswith("sqlalchemy"):
            return
        if record.name.startswith("uvicorn"):
            # Keep uvicorn logs as well, but still avoid recursion.
            pass

        try:
            self._in_emit = True

            from sqlmodel import Session
            from ..models.database import AuditLog

            user_id = _current_user_id.get()
            path = _current_path.get()

            action = f"LOG/{record.levelname}"
            details = record.getMessage()
            if path:
                details = f"[{path}] {details}"

            # Add basic origin for debugging.
            details = f"{details} (logger={record.name})"

            with Session(self._engine) as session:
                session.add(
                    AuditLog(
                        user_id=user_id,
                        action=action,
                        details=details,
                        created_at=datetime.utcnow(),
                    )
                )
                session.commit()
        except Exception:
            # Never raise from logging.
            return
        finally:
            self._in_emit = False


def configure_audit_logging(engine) -> None:
    handler = DBAuditLogHandler(engine)

    # Attach to root and common uvicorn loggers.
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    logging.getLogger("uvicorn").addHandler(handler)
    logging.getLogger("uvicorn.error").addHandler(handler)
    logging.getLogger("uvicorn.access").addHandler(handler)

    # Keep SQLAlchemy engine logs out of AuditLog by default.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
