"""
Defines the FastAPI application and endpoints as thin wrappers over the core modules.
"""

from fastapi import FastAPI

app = FastAPI(title="DriftLab API")

@app.get("/")
def read_root():
    return {"status": "ok"}
