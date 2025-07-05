from sqlalchemy.orm import Session
from models import engine, User
from sqlalchemy import select


def append_user(id: int, name: str, telephone: str):
    stmt = select(User).where(User.name.in_([name]))
    with Session(engine) as session:
        result = session.execute(stmt).scalars().all()

        if not result:
            print("Результат пустой")
            spongebob = User(
                id=id,
                name=name,
                telephone=telephone)
            session.add_all([spongebob])
            session.commit()
            print(f"Позьзователь {name} добавлен в базу")
            return True
        else:
            print("Найдено:", name)
            return False


append_user(777, "Spongebob", "8888888")

