import subprocess
from pathlib import Path

from app.config import AUDIVERIS_DOCKER_IMAGE
from app.config import MIN_IMAGE_LONG_EDGE
from PIL import Image


def _upscale_if_needed(image_path: Path) -> Path:
    with Image.open(image_path) as im:
        long_edge = max(im.size)
        if long_edge >= MIN_IMAGE_LONG_EDGE:
            return image_path

        factor = MIN_IMAGE_LONG_EDGE / long_edge
        new_size = (round(im.width * factor), round(im.height * factor))
        upscaled = im.convert("RGB").resize(new_size, Image.LANCZOS)

        out_path = image_path.with_name(f"upscaled_{image_path.stem}.png")
        upscaled.save(out_path)
        return out_path


def run_omr(input_path: Path, job_dir: Path) -> Path:
    """Run Audiveris OMR (in Docker) on input_path and return the produced MusicXML path.

    input_path must already live inside job_dir, since job_dir is bind-mounted
    into the container as /data.
    """
    source = input_path
    if input_path.suffix.lower() != ".pdf":
        source = _upscale_if_needed(input_path)

    out_dir = job_dir / "omr_out"
    out_dir.mkdir(exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{job_dir}:/data",
        AUDIVERIS_DOCKER_IMAGE,
        "-export",
        "-output", f"/data/{out_dir.name}",
        f"/data/{source.name}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    mxl_files = sorted(out_dir.glob("*.mxl"))
    if mxl_files:
        return mxl_files[0]

    log_files = sorted(out_dir.glob("*.log"))
    if log_files:
        detail = log_files[-1].read_text(errors="ignore")[-3000:]
    else:
        detail = (result.stderr or result.stdout or "")[-3000:]
    raise RuntimeError(f"楽譜を認識できませんでした。画像の解像度や傾きを確認してください。\n詳細: {detail}")
