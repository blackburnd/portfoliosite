import strawberry
from typing import List

# Define a placeholder type
@strawberry.type
class Book:
    title: str
    author: str

# Define a placeholder query
@strawberry.type
class Query:
    @strawberry.field
    def books(self) -> List[Book]:
        return [
            Book(title="The Great Gatsby", author="F. Scott Fitzgerald"),
        ]

# Create the schema
schema = strawberry.Schema(query=Query)
