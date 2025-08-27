# main.py - Lightweight FastAPI application with GraphQL
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
import uvicorn
import os

from app.resolvers import schema
from database import init_database, close_database

# Initialize FastAPI app
app = FastAPI(
    title="Portfolio API",
    description="Lightweight GraphQL API for Daniel's Portfolio Website",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL router
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

# Static files and templates (create directories if they don't exist)
os.makedirs("assets", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")

# Database initialization
@app.on_event("startup")
async def startup_event():
    await init_database()

@app.on_event("shutdown")
async def shutdown_event():
    await close_database()

# Routes for serving the portfolio website
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main portfolio page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Daniel Blackburn - Building innovative solutions"
    })

@app.get("/contact/", response_class=HTMLResponse)
async def contact(request: Request):
    """Serve the contact page"""
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "title": "Contact - Daniel Blackburn"
    })

@app.get("/work/", response_class=HTMLResponse)
async def work(request: Request):
    """Serve the work page"""
    return templates.TemplateResponse("work.html", {
        "request": request,
        "title": "Work - David Simmer"
    })

@app.get("/work/{project_slug}/", response_class=HTMLResponse)
async def project_detail(request: Request, project_slug: str):
    """Serve individual project pages"""
    return templates.TemplateResponse("project.html", {
        "request": request,
        "project_slug": project_slug,
        "title": f"Project - David Simmer"
    })

@app.get("/resume/", response_class=HTMLResponse)
async def resume(request: Request):
    """Serve the resume page"""
    return templates.TemplateResponse("resume.html", {
        "request": request,
        "title": "Resume - David Simmer"
    })

# API health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "portfolio-api"}

# GraphQL Playground (development only)
@app.get("/playground", response_class=HTMLResponse)
async def graphql_playground():
    """Serve GraphQL Playground for development"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GraphQL Playground</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
        <link rel="shortcut icon" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/favicon.png" />
    </head>
    <body>
        <div id="root"></div>
        <script>
            window.addEventListener('load', function (event) {
                GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: '/graphql'
                })
            })
        </script>
        <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        debug=True
    )
