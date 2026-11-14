import subprocess
from pathlib import Path
from typing import List

from app.config import AUDIVERIS_DOCKER_IMAGE
from app.config import MAX_PIXEL_COUNT
from app.config import MIN_IMAGE_LONG_EDGE
from app.config import PDF_MAX_DPI
from app.config import PDF_MIN_DPI
from app.config import PDF_TARGET_LONG_EDGE
from PIL import Image
from pypdf import PdfReader


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


def _pdf_page_sources(pdf_path: Path, job_dir: Path) -> List[Path]:
    """Rasterize each page of pdf_path to its own PNG and return the paths.

    Audiveris can read PDFs directly, but it rasterizes internally at a
    fixed ~300 DPI target computed off the PDF's page-size metadata. Many
    phone-scanner apps report an oversized physical page size for an
    otherwise modest embedded image, which makes Audiveris blow the page up
    to 80M+ pixels and time out. Rendering ourselves, at a DPI chosen from
    the actual page size so the long edge lands near PDF_TARGET_LONG_EDGE,
    avoids that.
    """
    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    box = reader.pages[0].mediabox
    long_edge_pts = max(float(box.width), float(box.height))
    dpi = round(72 * PDF_TARGET_LONG_EDGE / long_edge_pts)
    dpi = max(PDF_MIN_DPI, min(PDF_MAX_DPI, dpi))

    prefix = job_dir / "pdfpage"
    cmd = ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)

    pages = sorted(job_dir.glob("pdfpage-*.png"))
    if len(pages) != page_count:
        raise RuntimeError(
            f"PDFのページ画像化に失敗しました ({len(pages)}/{page_count} ページ)"
        )
    return pages


def run_omr(input_path: Path, job_dir: Path) -> List[Path]:
    """Run Audiveris OMR (in Docker) on input_path and return the produced
    MusicXML path(s), one per page, in page order.

    input_path must already live inside job_dir, since job_dir is bind-mounted
    into the container as /data.
    """
    if input_path.suffix.lower() == ".pdf":
        sources = _pdf_page_sources(input_path, job_dir)
    else:
        sources = [_upscale_if_needed(input_path)]

    out_dir = job_dir / "omr_out"
    out_dir.mkdir(exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{job_dir}:/data",
        AUDIVERIS_DOCKER_IMAGE,
        "-export",
        "-constant", f"org.audiveris.omr.step.LoadStep.maxPixelCount={MAX_PIXEL_COUNT}",
        "-output", f"/data/{out_dir.name}",
        *(f"/data/{s.name}" for s in sources),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

    # Each source image is processed as its own single-sheet book (Audiveris
    # only treats a single multi-page input file, e.g. a PDF, as one
    # "multi-sheet" book), so one .mxl per page/source is expected here.
    mxl_by_stem = {p.stem: p for p in out_dir.glob("*.mxl")}
    ordered = [mxl_by_stem.get(s.stem) for s in sources]

    if all(ordered):
        return ordered

    failed_pages = [i + 1 for i, mxl in enumerate(ordered) if mxl is None]
    log_files = sorted(out_dir.glob("*.log"))
    detail = (
        log_files[-1].read_text(errors="ignore")[-3000:]
        if log_files
        else (result.stderr or result.stdout or "")[-3000:]
    )
    raise RuntimeError(
        f"{len(failed_pages)}/{len(sources)} ページで楽譜を認識できませんでした"
        f" (失敗したページ: {failed_pages})。画像の解像度や傾きを確認してください。\n詳細: {detail}"
    )
