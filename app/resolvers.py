import strawberry
from typing import List, Optional
from database import PortfolioDatabase

# Portfolio types for GraphQL
@strawberry.type
class WorkExperience:
    id: str
    company: str
    position: str
    location: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    description: Optional[str]
    is_current: bool
    company_url: Optional[str]

@strawberry.type
class Project:
    id: str
    title: str
    description: str
    url: Optional[str]
    image_url: Optional[str]
    technologies: List[str]

@strawberry.type
class Contact:
    email: str
    phone: Optional[str]
    vcard: Optional[str]

@strawberry.type
class SocialLinks:
    resume: Optional[str]
    resume_download: Optional[str]
    github: Optional[str]
    twitter: Optional[str]

@strawberry.type
class Portfolio:
    id: str
    name: str
    title: str
    bio: str
    tagline: Optional[str]
    profile_image: Optional[str]
    contact: Contact
    social_links: SocialLinks
    work_experience: List[WorkExperience]
    projects: List[Project]
    skills: List[str]
    created_at: str
    updated_at: str


@strawberry.type
class Book:
    title: str
    author: str

@strawberry.type
class Query:
    @strawberry.field
    async def portfolio(self, portfolio_id: str = "daniel-blackburn") -> Optional[Portfolio]:
        """Get portfolio data with work experience and projects"""
        data = await PortfolioDatabase.get_portfolio(portfolio_id)
        if not data:
            return None
        
        return Portfolio(
            id=data["id"],
            name=data["name"],
            title=data["title"],
            bio=data["bio"],
            tagline=data["tagline"],
            profile_image=data["profile_image"],
            contact=Contact(
                email=data["contact"]["email"],
                phone=data["contact"]["phone"],
                vcard=data["contact"]["vcard"]
            ),
            social_links=SocialLinks(
                resume=data["social_links"]["resume"],
                resume_download=data["social_links"]["resume_download"],
                github=data["social_links"]["github"],
                twitter=data["social_links"]["twitter"]
            ),
            work_experience=[
                WorkExperience(
                    id=work["id"],
                    company=work["company"],
                    position=work["position"],
                    location=work["location"],
                    start_date=work["start_date"],
                    end_date=work["end_date"],
                    description=work["description"],
                    is_current=work["is_current"],
                    company_url=work["company_url"]
                ) for work in data["work_experience"]
            ],
            projects=[
                Project(
                    id=proj["id"],
                    title=proj["title"],
                    description=proj["description"],
                    url=proj["url"],
                    image_url=proj["image_url"],
                    technologies=proj["technologies"] if isinstance(proj["technologies"], list) else []
                ) for proj in data["projects"]
            ],
            skills=data["skills"] if isinstance(data["skills"], list) else [],
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )
    
    @strawberry.field
    def books(self) -> List[Book]:
        """Legacy books query for backward compatibility"""
        return [
            Book(title="The Great Gatsby", author="F. Scott Fitzgerald"),
        ]

    @strawberry.field
    async def workExperience(self) -> List[WorkExperience]:
        import os
        import databases
        DATABASE_URL = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
        db = databases.Database(DATABASE_URL)
        await db.connect()
        rows = await db.fetch_all("SELECT id, company, position, location, start_date, end_date, description, is_current, company_url FROM work_experience ORDER BY sort_order, start_date DESC")
        await db.disconnect()
        return [
            WorkExperience(
                id=str(row["id"]),
                company=row["company"],
                position=row["position"],
                location=row["location"],
                start_date=(str(row["start_date"])
                            if row["start_date"] else None),
                end_date=str(row["end_date"]) if row["end_date"] else None,
                description=row["description"],
                is_current=row["is_current"],
                company_url=row["company_url"]
            ) for row in rows
        ]


# Create the schema
schema = strawberry.Schema(query=Query)
