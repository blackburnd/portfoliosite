from fastapi import FastAPI

app = FastAPI()

@app.get("/profile")
def get_profile():
    return {"name": "Your Name", "bio": "Short bio here."}

@app.get("/portfolio")
def get_portfolio():
    return {"projects": [
        {"title": "Project 1", "description": "Description of project 1."},
        {"title": "Project 2", "description": "Description of project 2."}
    ]}
