from sqlmodel import Session, create_engine, select
from app.models.database import User
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
)

def reset_user_lock(username: str):
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        if user:
            user.device_id = None
            session.add(user)
            session.commit()
            print(f"Device lock for user '{username}' has been reset!")
        else:
            print(f"User '{username}' not found.")

if __name__ == "__main__":
    reset_user_lock("user1")
