from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.auth_rbac.models import Role, User

DEFAULT_ROLES = [
    ("Admin", "Full administrative access to users, settings, simulations, and remediations."),
    (
        "Operations Engineer",
        "Can investigate incidents, run simulations, and approve remediations.",
    ),
    ("Viewer", "Read-only access to dashboards, telemetry, incidents, and reports."),
]

DEFAULT_USERS = [
    ("admin@opsmind.local", "Aakash Kumar Mishra", "Admin123!", ["Admin"]),
    ("sre@opsmind.local", "Priya Nair (SRE)", "OpsEng123!", ["Operations Engineer"]),
    ("viewer@opsmind.local", "Jordan Lee (Ops Manager)", "Viewer123!", ["Viewer"]),
]


async def seed_auth_data(db: AsyncSession) -> None:
    role_map: dict[str, Role] = {}
    for role_name, description in DEFAULT_ROLES:
        res = await db.execute(select(Role).where(Role.name == role_name))
        role = res.scalar_one_or_none()
        if role is None:
            role = Role(name=role_name, description=description)
            db.add(role)
            await db.flush()
        role_map[role_name] = role

    for email, full_name, raw_password, role_names in DEFAULT_USERS:
        res = await db.execute(select(User).where(User.email == email))
        if res.scalar_one_or_none() is None:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(raw_password),
                roles=[role_map[r] for r in role_names],
            )
            db.add(user)

    await db.commit()
    