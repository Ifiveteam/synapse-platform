import os
import tempfile

from fastapi import APIRouter, File, UploadFile

from app.agents.indexer.graph import graph

router = APIRouter(prefix="/indexer", tags=["indexer"])


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):  # noqa: B008
    """테이크아웃 JSON 파일 업로드 → 분석 시작"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    result = graph.invoke(
        {
            "json_path": tmp_path,
            "raw_data": [],
            "cleaned_data": [],
            "error": None,
            "saved_count": None,
        }
    )

    os.unlink(tmp_path)

    if result["error"]:
        return {"status": "error", "message": result["error"]}

    return {
        "status": "success",
        "total": len(result["raw_data"]),
        "processed": result["saved_count"],
    }


@router.get("/status")
def status():
    """인덱서 상태 확인"""
    return {"status": "running"}
