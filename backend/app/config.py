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
