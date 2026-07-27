from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.models import Role, TrainingTemplate, User
from runscope_api.security import hash_password, normalize_email
from runscope_api.templates.registry import registry


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


async def seed_training_templates(session: AsyncSession) -> int:
    created = 0
    for definition in registry.all():
        template = await session.scalar(
            select(TrainingTemplate).where(
                TrainingTemplate.key == definition.key,
                TrainingTemplate.version == definition.version,
            )
        )
        if template is None:
            template = TrainingTemplate(
                key=definition.key,
                name=definition.name,
                description=definition.description,
                version=definition.version,
                parameter_schema=definition.parameter_schema,
                enabled=True,
            )
            session.add(template)
            created += 1
        else:
            template.name = definition.name
            template.description = definition.description
            template.parameter_schema = definition.parameter_schema
    await session.commit()
    return created


async def seed_demo_data(session: AsyncSession) -> tuple[int, int]:
    users = await seed_demo_users(session)
    templates = await seed_training_templates(session)
    return users, templates
