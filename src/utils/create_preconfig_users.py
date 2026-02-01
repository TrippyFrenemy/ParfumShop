from src.database import async_session_maker
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.auth.dependencies import pwd_context
from src.users.models import User, UserRole

async def create_user(email, name, role, password):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✅ {role} уже существует, пропускаем создание")
            return

        try:
            user = User(
                email=email,
                name=name,
                role=UserRole(role.lower()),
                hashed_password=pwd_context.hash(password),
            )
            session.add(user)
            await session.commit()
            print(f"✅ {role} создан")
        except IntegrityError:
            print(f"⚠️ {role} уже есть (integrity check)")
