from typing import Literal
from typing import Optional

from pydantic import BaseModel


class JobStatus(BaseModel):
    job_id: str
    status: Literal[
        "omr_processing",
        "omr_failed",
        "ready",
        "rendering",
        "done",
        "render_failed",
    ]
    detected_key: Optional[str] = None
    part_count: Optional[int] = None
    measure_count: Optional[int] = None
    error: Optional[str] = None


class TransposeRequest(BaseModel):
    mode: Literal["semitones", "key"]
    semitones: Optional[int] = None
    target_key: Optional[str] = None
