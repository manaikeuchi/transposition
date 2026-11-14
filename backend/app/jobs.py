from __future__ import annotations

import copy
import multiprocessing
import shutil
import uuid
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import List
from typing import Optional

from app.config import DATA_DIR
from app.schemas import JobStatus
from app.services import omr
from app.services import render
from app.services import transpose
from fastapi import UploadFile
from music21 import stream
from pypdf import PdfReader
from pypdf import PdfWriter

_executor = ThreadPoolExecutor(max_workers=2)

# verovio's native extension aborts the whole process if its toolkit is ever
# constructed off the main thread, so rendering runs in a separate process
# (spawned, not forked, since forking a multi-threaded process is unsafe).
_render_pool = ProcessPoolExecutor(
    max_workers=2, mp_context=multiprocessing.get_context("spawn")
)


@dataclass
class Job:
    job_id: str
    job_dir: Path
    status: str = "omr_processing"
    musicxml_paths: List[Path] = field(default_factory=list)
    output_pdf_path: Optional[Path] = None
    detected_key: Optional[str] = None
    part_count: Optional[int] = None
    measure_count: Optional[int] = None
    error: Optional[str] = None

    def to_schema(self) -> JobStatus:
        return JobStatus(
            job_id=self.job_id,
            status=self.status,
            detected_key=self.detected_key,
            part_count=self.part_count,
            measure_count=self.measure_count,
            error=self.error,
        )


_jobs: dict[str, Job] = {}


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


async def create_job(upload: UploadFile) -> Job:
    job_id = uuid.uuid4().hex
    job_dir = DATA_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload.filename or "input").suffix.lower() or ".bin"
    input_path = job_dir / f"input{suffix}"
    with open(input_path, "wb") as f:
        shutil.copyfileobj(upload.file, f)

    job = Job(job_id=job_id, job_dir=job_dir)
    _jobs[job_id] = job

    _executor.submit(_run_omr_stage, job, input_path)
    return job


def _run_omr_stage(job: Job, input_path: Path) -> None:
    try:
        mxl_paths = omr.run_omr(input_path, job.job_dir)
        scores = [transpose.load_score(p) for p in mxl_paths]

        try:
            # The first page's key is taken as representative of the piece.
            job.detected_key = str(transpose.analyze_key(scores[0]))
        except Exception:
            # Key estimation is best-effort (e.g. very short or atonal
            # excerpts can make music21's key-finder fail); it's only
            # informational, so don't fail the whole job over it.
            job.detected_key = None

        job.musicxml_paths = mxl_paths
        job.part_count = len(scores[0].parts) if scores[0].parts else 1
        job.measure_count = sum(
            len(s.parts[0].getElementsByClass("Measure")) if s.parts else 0 for s in scores
        )
        job.status = "ready"
    except Exception as exc:  # noqa: BLE001
        job.status = "omr_failed"
        job.error = str(exc)


def start_transpose(job: Job, mode: str, semitones: Optional[int], target_key: Optional[str]) -> None:
    job.status = "rendering"
    job.error = None
    _executor.submit(_run_transpose_stage, job, mode, semitones, target_key)


def _export_musicxml(score: stream.Score, output_xml: Path) -> None:
    """Write score as MusicXML, falling back through increasingly lossy
    strategies for OMR output with irregular/inconsistent rhythm that trips
    up music21's notation-fixup pass on export (duplicate-measure errors,
    "complex durations" errors, etc). Pitches are always preserved; only
    automatic tie/rest cleanup may be skipped or ties stripped.

    Each attempt gets its own deep copy: a failed write() can leave the
    stream mutated, which would otherwise corrupt the next fallback too.
    """
    attempts = [
        lambda s: s.write("musicxml", fp=str(output_xml)),
        lambda s: s.write("musicxml", fp=str(output_xml), makeNotation=False),
        lambda s: s.stripTies(inPlace=False).write(
            "musicxml", fp=str(output_xml), makeNotation=False
        ),
    ]
    last_exc = None
    for attempt in attempts:
        try:
            attempt(copy.deepcopy(score))
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise last_exc


def _merge_pdfs(pdf_paths: List[Path], output_pdf: Path) -> None:
    writer = PdfWriter()
    for pdf_path in pdf_paths:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)
    with open(output_pdf, "wb") as f:
        writer.write(f)


def _run_transpose_stage(
    job: Job,
    mode: str,
    semitones: Optional[int],
    target_key: Optional[str],
) -> None:
    try:
        page_pdfs = []
        for i, mxl_path in enumerate(job.musicxml_paths):
            score = transpose.load_score(mxl_path)
            new_score, _applied = transpose.transpose_score(
                score, mode=mode, semitones=semitones, target_key_name=target_key
            )

            output_xml = job.job_dir / f"transposed-{i:03d}.musicxml"
            _export_musicxml(new_score, output_xml)

            page_pdf = job.job_dir / f"page-{i:03d}.pdf"
            _render_pool.submit(render.render_score_to_pdf, output_xml, page_pdf).result()
            page_pdfs.append(page_pdf)

        output_pdf = job.job_dir / "output.pdf"
        if len(page_pdfs) == 1:
            page_pdfs[0].replace(output_pdf)
        else:
            _merge_pdfs(page_pdfs, output_pdf)

        job.output_pdf_path = output_pdf
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status = "render_failed"
        job.error = str(exc)
