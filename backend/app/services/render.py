from pathlib import Path

import cairosvg
import img2pdf
import verovio

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

# Verovio's SVG glyphs rely on an author-set overflow="inherit" on <symbol>
# to opt out of the SVG default symbol clip. Several PDF viewers don't
# resolve that correctly and clip every glyph to its nominal glyph box
# instead (seen as note/clef/etc. symbols showing only their bottom half,
# while plain-path elements like staff lines and slurs render fine). Side-
# step the whole vector-glyph compatibility question by rasterizing with
# cairosvg (which does resolve it correctly) and embedding that as a
# full-page image, rather than converting the SVG to PDF vectors directly.
RASTER_SCALE = 4.0


def render_score_to_pdf(musicxml_path: Path, pdf_path: Path) -> None:
    tk = verovio.toolkit()
    tk.setOptions(VEROVIO_OPTIONS)
    if not tk.loadFile(str(musicxml_path)):
        raise RuntimeError("楽譜データのレンダリングに失敗しました")

    page_count = tk.getPageCount()
    page_pngs = []
    for page in range(1, page_count + 1):
        svg = tk.renderToSVG(page)
        page_pngs.append(
            cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                scale=RASTER_SCALE,
                background_color="white",
            )
        )

    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(page_pngs))
