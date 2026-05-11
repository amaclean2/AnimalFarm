from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
async def list_logs() -> list[dict]:
    if not LOGS_DIR.exists():
        return []
    files = sorted(LOGS_DIR.glob("game_*.json"), reverse=True)
    return [
        {
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "modified": f.stat().st_mtime,
        }
        for f in files
    ]


@router.get("/{filename}")
async def get_log(filename: str) -> FileResponse:
    if not filename.endswith(".json") or "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = LOGS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Log not found")
    return FileResponse(path, media_type="application/json", filename=filename)
