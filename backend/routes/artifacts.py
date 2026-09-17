"""
Artifact inspection and download routes for TaskFlow AI.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from taskflow import config

artifacts_router = APIRouter(tags=["Artifacts"])


@artifacts_router.get("/api/artifacts")
def list_artifacts():
    """List all generated reports and cleaned datasets."""
    artifacts = []

    # Reports
    if config.REPORTS_DIR.exists():
        for f in config.REPORTS_DIR.glob("*"):
            if f.is_file():
                artifacts.append({
                    "name": f.name,
                    "type": "Report",
                    "extension": f.suffix,
                    "size_bytes": f.stat().st_size,
                    "path": f"/api/artifacts/{f.name}?type=report",
                })

    # Cleaned Datasets
    if config.CLEANED_DATA_DIR.exists():
        for f in config.CLEANED_DATA_DIR.glob("*"):
            if f.is_file():
                artifacts.append({
                    "name": f.name,
                    "type": "Cleaned Data",
                    "extension": f.suffix,
                    "size_bytes": f.stat().st_size,
                    "path": f"/api/artifacts/{f.name}?type=data",
                })

    return artifacts


@artifacts_router.get("/api/artifacts/{filename}")
def get_artifact(filename: str, type: str = "report"):
    """Download or stream an artifact file."""
    if type == "report":
        file_path = config.REPORTS_DIR / filename
    else:
        file_path = config.CLEANED_DATA_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    return FileResponse(file_path)
