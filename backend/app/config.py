from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data" / "jobs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

AUDIVERIS_DOCKER_IMAGE = "audiveris-omr:5.11.0"

ALLOWED_UPLOAD_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# Images whose longer edge is below this many pixels are upscaled before
# being handed to Audiveris, since OMR needs a minimum staff-line spacing
# (interline) in pixels to reliably detect staves (roughly a 300 DPI scan).
MIN_IMAGE_LONG_EDGE = 2000

# PDF pages are rasterized ourselves (via pdftoppm) at a DPI chosen so the
# longer edge lands near this many pixels, rather than letting Audiveris
# rasterize the PDF internally: Audiveris targets ~300 DPI off of the PDF's
# (often wrong/oversized) page-size metadata, which can blow a normal
# phone-scanned page up past 80M+ pixels and make processing time out.
PDF_TARGET_LONG_EDGE = 2200
PDF_MIN_DPI = 100
PDF_MAX_DPI = 300

# Audiveris rejects any sheet above this pixel count as a safety cap
# (default 20,000,000). Kept generous as a backstop in case a page still
# ends up large; 0 would disable the check entirely but risks unbounded
# memory use on a pathological upload.
MAX_PIXEL_COUNT = 200_000_000
