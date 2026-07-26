from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.models import Role, User
from runscope_api.security import hash_password, normalize_email


@dataclass(frozen=True)
class DemoUser:
    email: str
    password: str
    role: Role


DEMO_USERS = (
    DemoUser("viewer@runscope.dev", "ViewerDemo123!", Role.VIEWER),
    DemoUser("researcher@runscope.dev", "ResearcherDemo123!", Role.RESEARCHER),
    DemoUser("admin@runscope.dev", "AdminDemo123!", Role.ADMINISTRATOR),
)


async def seed_demo_users(session: AsyncSession) -> int:
    created = 0
    for demo in DEMO_USERS:
        email = normalize_email(demo.email)
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(demo.password),
                    role=demo.role,
                )
            )
            created += 1
        else:
            user.role = demo.role
            if not user.password_hash:
                user.password_hash = hash_password(demo.password)
    await session.commit()
    return created
