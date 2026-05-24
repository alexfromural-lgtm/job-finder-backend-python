"""
Seed script — mirrors prisma/seed.ts.

Run with:
    python scripts/seed.py
"""

import asyncio
import sys
import os

# Ensure the project root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User, Role
from app.models.profiles import JobSeekerProfile, RecruiterProfile
from app.models.job import Job
from app.utils.hash import hash_password


SEED_RECRUITER = {
    "name": "Acme Corp",
    "email": "recruiter@acme.com",
    "password": "password123",
    "company_name": "Acme Corporation",
    "company_website": "https://acme.com",
    "description": "A global leader in innovative solutions.",
    "industry": "Technology",
}

SEED_JOB_SEEKER = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "password": "password123",
    "bio": "Passionate software developer with 3 years of experience.",
    "location": "San Francisco, CA",
    "skills": ["Python", "FastAPI", "PostgreSQL", "React"],
    "education": "B.Sc. Computer Science, Stanford University",
    "experience": "3 years backend development",
}

SEED_JOBS = [
    {
        "title": "Senior Python Developer",
        "description": "Join our backend team building scalable microservices.",
        "requirements": "5+ years Python, FastAPI or Django, PostgreSQL, Docker.",
        "location": "Remote",
        "salary_range": "$120,000 - $160,000",
        "category": "Engineering",
    },
    {
        "title": "Frontend React Engineer",
        "description": "Build beautiful, responsive UIs for our SaaS platform.",
        "requirements": "3+ years React, TypeScript, REST APIs.",
        "location": "New York, NY",
        "salary_range": "$100,000 - $140,000",
        "category": "Engineering",
    },
    {
        "title": "Product Manager",
        "description": "Drive product strategy and roadmap for our core product.",
        "requirements": "3+ years product management, agile methodology.",
        "location": "San Francisco, CA",
        "salary_range": "$110,000 - $150,000",
        "category": "Product",
    },
]


async def seed(db: AsyncSession) -> None:
    print("🌱 Seeding database...")

    # ── Recruiter ────────────────────────────────────────────────────────────
    from sqlalchemy import select

    existing = await db.execute(
        select(User).where(User.email == SEED_RECRUITER["email"])
    )
    if existing.scalar_one_or_none():
        print(f"  ⚡ Recruiter {SEED_RECRUITER['email']} already exists, skipping.")
    else:
        recruiter_user = User(
            name=SEED_RECRUITER["name"],
            email=SEED_RECRUITER["email"],
            password=hash_password(SEED_RECRUITER["password"]),
            roles=[Role.RECRUITER],
        )
        db.add(recruiter_user)
        await db.flush()

        recruiter_profile = RecruiterProfile(
            user_id=recruiter_user.id,
            company_name=SEED_RECRUITER["company_name"],
            company_website=SEED_RECRUITER["company_website"],
            description=SEED_RECRUITER["description"],
            industry=SEED_RECRUITER["industry"],
        )
        db.add(recruiter_profile)
        await db.flush()

        # ── Jobs ─────────────────────────────────────────────────────────────
        for job_data in SEED_JOBS:
            db.add(
                Job(
                    recruiter_id=recruiter_profile.id,
                    **job_data,
                )
            )

        print(f"  ✅ Created recruiter: {SEED_RECRUITER['email']}")
        print(f"  ✅ Created {len(SEED_JOBS)} jobs")

    # ── Job Seeker ────────────────────────────────────────────────────────────
    existing_js = await db.execute(
        select(User).where(User.email == SEED_JOB_SEEKER["email"])
    )
    if existing_js.scalar_one_or_none():
        print(f"  ⚡ Job seeker {SEED_JOB_SEEKER['email']} already exists, skipping.")
    else:
        js_user = User(
            name=SEED_JOB_SEEKER["name"],
            email=SEED_JOB_SEEKER["email"],
            password=hash_password(SEED_JOB_SEEKER["password"]),
            roles=[Role.JOB_SEEKER],
        )
        db.add(js_user)
        await db.flush()

        db.add(
            JobSeekerProfile(
                user_id=js_user.id,
                bio=SEED_JOB_SEEKER["bio"],
                location=SEED_JOB_SEEKER["location"],
                skills=SEED_JOB_SEEKER["skills"],
                education=SEED_JOB_SEEKER["education"],
                experience=SEED_JOB_SEEKER["experience"],
            )
        )
        print(f"  ✅ Created job seeker: {SEED_JOB_SEEKER['email']}")

    await db.commit()
    print("✅ Seeding complete!")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
