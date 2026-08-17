import os
import re
import uuid

from docx import Document
from docx.shared import Pt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit

from pptx import Presentation


# =========================================================
# CONFIG
# =========================================================

FILES_DIR = "files"
os.makedirs(FILES_DIR, exist_ok=True)


# =========================================================
# FILENAME
# =========================================================

def _clean_filename(text, default="perla_file"):
    text = (text or default).strip()

    text = re.sub(
        r"[^\w\u0600-\u06FF\- ]",
        "",
        text
    )

    text = text.replace(" ", "_")

    return text[:40] or default


# =========================================================
# WORD
# =========================================================

def create_docx(content, title=None):

    doc = Document()

    # Title
    if title:
        doc.add_heading(
            title,
            level=1
        )

    # Content
    for paragraph in (content or "").split("\n"):

        paragraph = paragraph.strip()

        if paragraph:

            p = doc.add_paragraph(
                paragraph
            )

            for run in p.runs:
                run.font.size = Pt(12)

        else:
            doc.add_paragraph("")

    filename = (
        f"{_clean_filename(title, 'perla_word')}_"
        f"{uuid.uuid4().hex[:8]}.docx"
    )

    path = os.path.join(
        FILES_DIR,
        filename
    )

    doc.save(path)

    print(
        f"[PERLA FILE] Word created: {path}"
    )

    return path, filename


# =========================================================
# PDF
# =========================================================

def _register_arabic_font():

    """
    نحاول تسجيل خط عربي موجود على Windows.
    لو مش موجود، نرجع لـ Helvetica.
    """

    possible_fonts = [
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]

    for font_path in possible_fonts:

        if os.path.exists(font_path):

            try:

                pdfmetrics.registerFont(
                    TTFont(
                        "PerlaArabic",
                        font_path
                    )
                )

                return "PerlaArabic"

            except Exception:
                pass

    return "Helvetica"


def create_pdf(content, title=None):

    filename = (
        f"{_clean_filename(title, 'perla_pdf')}_"
        f"{uuid.uuid4().hex[:8]}.pdf"
    )

    path = os.path.join(
        FILES_DIR,
        filename
    )

    c = canvas.Canvas(
        path,
        pagesize=A4
    )

    width, height = A4

    margin = 2 * cm

    y = height - margin

    font_name = _register_arabic_font()

    font_size = 12

    c.setFont(
        font_name,
        font_size
    )

    max_width = width - (
        2 * margin
    )

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    if title:

        c.setFont(
            font_name,
            18
        )

        c.drawString(
            margin,
            y,
            title
        )

        y -= 1.5 * cm

        c.setFont(
            font_name,
            font_size
        )

    # -----------------------------------------------------
    # CONTENT
    # -----------------------------------------------------

    for raw_line in (content or "").split("\n"):

        raw_line = raw_line.strip()

        if not raw_line:

            y -= 0.4 * cm

            continue

        lines = simpleSplit(
            raw_line,
            font_name,
            font_size,
            max_width
        )

        if not lines:
            lines = [""]

        for line in lines:

            # New page
            if y < margin:

                c.showPage()

                c.setFont(
                    font_name,
                    font_size
                )

                y = height - margin

            c.drawString(
                margin,
                y,
                line
            )

            y -= 0.65 * cm

    c.save()

    print(
        f"[PERLA FILE] PDF created: {path}"
    )

    return path, filename


# =========================================================
# POWERPOINT
# =========================================================

def create_pptx(content, title=None):

    prs = Presentation()

    # -----------------------------------------------------
    # Split content into sections
    # -----------------------------------------------------

    parts = [
        p.strip()
        for p in (content or "").split("\n\n")
        if p.strip()
    ]

    # لو المحتوى كله فقرة واحدة
    if not parts:

        parts = [
            content or "عرض تقديمي بيرلا"
        ]

    # -----------------------------------------------------
    # Title slide
    # -----------------------------------------------------

    title_slide_layout = (
        prs.slide_layouts[0]
    )

    title_slide = prs.slides.add_slide(
        title_slide_layout
    )

    title_shape = title_slide.shapes.title

    if title_shape:

        title_shape.text = (
            title or "عرض تقديمي"
        )

    # -----------------------------------------------------
    # Content slides
    # -----------------------------------------------------

    content_slide_layout = (
        prs.slide_layouts[1]
    )

    for index, part in enumerate(parts):

        slide = prs.slides.add_slide(
            content_slide_layout
        )

        # Slide title
        if slide.shapes.title:

            slide.shapes.title.text = (
                f"نقطة {index + 1}"
            )

        # Content
        try:

            placeholder = (
                slide.placeholders[1]
            )

            placeholder.text_frame.text = part

        except Exception:

            # لو الـlayout مختلف
            textbox = slide.shapes.add_textbox(
                cm,
                4 * cm,
                width=width if "width" in locals() else 20 * cm,
                height=10 * cm
            )

            textbox.text_frame.text = part

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    filename = (
        f"{_clean_filename(title, 'perla_pptx')}_"
        f"{uuid.uuid4().hex[:8]}.pptx"
    )

    path = os.path.join(
        FILES_DIR,
        filename
    )

    prs.save(path)

    print(
        f"[PERLA FILE] PowerPoint created: {path}"
    )

    return path, filename
