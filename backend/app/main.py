from pathlib import Path

from app import jobs
from app.config import ALLOWED_UPLOAD_SUFFIXES
from app.schemas import JobStatus
from app.schemas import TransposeRequest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI(title="Transposition API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/jobs", response_model=JobStatus)
async def upload_score(file: UploadFile) -> JobStatus:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"対応していないファイル形式です ({suffix or '不明'})。PDF/JPEG/PNG をアップロードしてください。",
        )

    job = await jobs.create_job(file)
    return job.to_schema()


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    return job.to_schema()


@app.post("/api/jobs/{job_id}/transpose", response_model=JobStatus)
async def transpose_job(job_id: str, req: TransposeRequest) -> JobStatus:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    if job.status not in ("ready", "done", "render_failed"):
        raise HTTPException(status_code=409, detail=f"現在のジョブ状態 ({job.status}) では移調できません")

    jobs.start_transpose(job, req.mode, req.semitones, req.target_key)
    return job.to_schema()


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str) -> FileResponse:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    if job.status != "done" or job.output_pdf_path is None:
        raise HTTPException(status_code=409, detail="PDF はまだ準備できていません")

    return FileResponse(
        path=job.output_pdf_path,
        media_type="application/pdf",
        filename="transposed.pdf",
    )
