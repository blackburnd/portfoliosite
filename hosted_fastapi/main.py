"""Main FastAPI application module."""

from fastapi import FastAPI

app = FastAPI(
    title="Hosted FastAPI",
    description="A FastAPI application for hosting and deployment",
    version="0.1.0"
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Hosted FastAPI"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)