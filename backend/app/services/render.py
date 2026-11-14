import io
from pathlib import Path

import cairosvg
import verovio
from pypdf import PdfReader
from pypdf import PdfWriter

VEROVIO_OPTIONS = {
    "pageWidth": 2100,
    "pageHeight": 2970,
    "scale": 40,
    "adjustPageHeight": True,
    "breaks": "auto",
    # OMR output's title/composer metadata is usually just the source
    # filename, not real information worth rendering on every page.
    "header": "none",
}


def render_score_to_pdf(musicxml_path: Path, pdf_path: Path) -> None:
    tk = verovio.toolkit()
    tk.setOptions(VEROVIO_OPTIONS)
    if not tk.loadFile(str(musicxml_path)):
        raise RuntimeError("楽譜データのレンダリングに失敗しました")

    page_count = tk.getPageCount()
    writer = PdfWriter()
    for page in range(1, page_count + 1):
        svg = tk.renderToSVG(page)
        page_pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
        reader = PdfReader(io.BytesIO(page_pdf_bytes))
        writer.add_page(reader.pages[0])

    with open(pdf_path, "wb") as f:
        writer.write(f)
