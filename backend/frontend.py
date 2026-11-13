"""Serve the built React app from the same origin as the API."""
import os
from pathlib import Path
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

class SPAFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or Path(path).suffix:
                raise
            return await super().get_response("index.html", scope)

def mount_frontend(app):
    directory = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[1] / "dist"))
    if (directory / "index.html").is_file():
        app.mount("/", SPAFiles(directory=directory, html=True), name="frontend")
