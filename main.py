from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, HTMLResponse
import os

app = FastAPI()

# Get the absolute path of the directory containing main.py
APP_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open(os.path.join(APP_DIR, "templates/index.html")) as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.get("/resume")
async def get_resume():
    file_path = os.path.join(APP_DIR, "resume.pdf")
    if os.path.exists(file_path):
        headers = {"Content-Disposition": "inline; filename=resume.pdf"}
        return FileResponse(
            file_path,
            media_type='application/pdf',
            headers=headers
        )
    return Response(status_code=404)
