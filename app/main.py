from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from strawberry.fastapi import GraphQLRouter
import app.resolvers as resolvers
import databases
import os

app = FastAPI()

# GraphQL endpoint
graphql_app = GraphQLRouter(resolvers.schema)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/profile")
def get_profile():
    return {"name": "Your Name", "bio": "Short bio here."}

@app.get("/portfolio")
def get_portfolio():
    return {"projects": [
        {"title": "Project 1", "description": "Description of project 1."},
        {"title": "Project 2", "description": "Description of project 2."}
    ]}

# /work page populated via GraphQL
@app.get("/work", response_class=HTMLResponse)
async def work_page():
    # Query GraphQL endpoint for work experience
    import httpx
    query = """
    query {
        workExperience {
            company
            position
            startDate
            endDate
            description
        }
    }
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:8000/graphql", json={"query": query})
        data = resp.json()
    work_items = data.get("data", {}).get("workExperience", [])
    html = "<h1>Work Experience</h1><ul>"
    for item in work_items:
        html += f"<li><strong>{item['company']}</strong> - {item['position']} ({item['startDate']} - {item.get('endDate','Present')})<br>{item['description']}</li>"
    html += "</ul>"
    return html

# /schema page returns DB schema info
@app.get("/schema", response_class=JSONResponse)
async def schema_page():
    # Connect to DB
    DATABASE_URL = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
    db = databases.Database(DATABASE_URL)
    await db.connect()
    # Get tables
    tables = await db.fetch_all("""
        SELECT table_name FROM information_schema.tables WHERE table_schema='public'
    """)
    result = {}
    for t in tables:
        table = t[0] if isinstance(t, tuple) else t['table_name']
        # Get columns
        columns = await db.fetch_all(f"""
            SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}'
        """)
        # Get count
        count = await db.fetch_val(f"SELECT COUNT(*) FROM {table}")
        result[table] = {
            "columns": [{"name": c[0] if isinstance(c, tuple) else c['column_name'], "type": c[1] if isinstance(c, tuple) else c['data_type']} for c in columns],
            "count": count
        }
    await db.disconnect()
    return result
