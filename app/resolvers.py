import strawberry
from typing import List

import databases
import os

# Define a placeholder type
@strawberry.type
class Book:
    title: str
    author: str

# WorkExperience type
@strawberry.type
class WorkExperience:
    company: str
    position: str
    startDate: str
    endDate: str
    description: str

@strawberry.type
class Query:
    @strawberry.field
    def books(self) -> List[Book]:
        return [
            Book(title="The Great Gatsby", author="F. Scott Fitzgerald"),
        ]

    @strawberry.field
    async def workExperience(self) -> List[WorkExperience]:
        DATABASE_URL = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
        db = databases.Database(DATABASE_URL)
        await db.connect()
        rows = await db.fetch_all("SELECT company, position, start_date, end_date, description FROM work_experience ORDER BY sort_order, start_date DESC")
        await db.disconnect()
        return [
            WorkExperience(
                company=row[0] if isinstance(row, tuple) else row["company"],
                position=row[1] if isinstance(row, tuple) else row["position"],
                startDate=row[2] if isinstance(row, tuple) else row["start_date"],
                endDate=row[3] if isinstance(row, tuple) else row["end_date"],
                description=row[4] if isinstance(row, tuple) else row["description"]
            ) for row in rows
        ]

# Create the schema
schema = strawberry.Schema(query=Query)
