import os
import re
import uuid

from docx import Document
from docx.shared import Pt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

from pptx import Presentation

FILES_DIR = "files"
os.makedirs(FILES_DIR, exist_ok=True)


def _clean_filename(text, default="perla_file"):
    text = (text or default).strip()
    text = re.sub(r"[^\w\u0600-\u06FF\- ]", "", text)
    text = text.replace(" ", "_")
    return text[:40] or default


def create_docx(content, title=None):
    doc = Document()

    if title:
        doc.add_heading(title, level=1)

    for paragraph in content.split("\n"):
        paragraph = paragraph.strip()
        if paragraph:
            p = doc.add_paragraph(paragraph)
            for run in p.runs:
                run.font.size = Pt(12)
        else:
            doc.add_paragraph("")

    filename = f"{_clean_filename(title)}_{uuid.uuid4().hex[:6]}.docx"
    path = os.path.join(FILES_DIR, filename)
    doc.save(path)
    return path, filename


def create_pdf(content, title=None):
    filename = f"{_clean_filename(title, 'perla_pdf')}_{uuid.uuid4().hex[:6]}.pdf"
    path = os.path.join(FILES_DIR, filename)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    margin = 2 * cm
    y = height - margin
    font_name = "Helvetica"
    font_size = 12
    c.setFont(font_name, font_size)

    max_width = width - 2 * margin

    if title:
        c.setFont(font_name, 16)
        c.drawString(margin, y, title)
        y -= 1.2 * cm
        c.setFont(font_name, font_size)

    for raw_line in content.split("\n"):
        lines = simpleSplit(raw_line, font_name, font_size, max_width) or [""]
        for line in lines:
            if y < margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = height - margin
            c.drawString(margin, y, line)
            y -= 0.6 * cm

    c.save()
    return path, filename


def create_pptx(content, title=None):
    prs = Presentation()

    parts = [p.strip() for p in content.split("\n\n") if p.strip()]
    slides_data = [
        {"title": f"نقطة {i + 1}", "content": part}
        for i, part in enumerate(parts)
    ] or [{"title": title or "بيرلا", "content": content}]

    title_slide_layout = prs.slide_layouts[0]
    content_slide_layout = prs.slide_layouts[1]

    title_slide = prs.slides.add_slide(title_slide_layout)
    title_slide.shapes.title.text = title or "عرض تقديمي"

    for item in slides_data:
        slide = prs.slides.add_slide(content_slide_layout)
        slide.shapes.title.text = item["title"]
        slide.placeholders[1].text_frame.text = item["content"]

    filename = f"{_clean_filename(title, 'perla_pptx')}_{uuid.uuid4().hex[:6]}.pptx"
    path = os.path.join(FILES_DIR, filename)
    prs.save(path)
    return path, filename
