from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _draw_wrapped_text(pdf: canvas.Canvas, text: str, x: int, y: int, width_chars: int = 108):
    lines = []
    for paragraph in text.splitlines() or [""]:
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        while len(paragraph) > width_chars:
            chunk = paragraph[:width_chars]
            split_at = chunk.rfind(" ")
            if split_at <= 0:
                split_at = width_chars
            lines.append(paragraph[:split_at].strip())
            paragraph = paragraph[split_at:].strip()
        lines.append(paragraph)

    for line in lines:
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 800
        pdf.drawString(x, y, line)
        y -= 14
    return y


def build_assessment_pdf(report_id: int, payload: dict, ai_report: str, username: str, created_label: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"Assessment Report {report_id}")

    y = 810
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "HealthSignal AI - Assessment Report")
    y -= 24

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Report ID: {report_id}")
    y -= 14
    pdf.drawString(40, y, f"User: {username}")
    y -= 14
    pdf.drawString(40, y, f"Created: {created_label}")
    y -= 20

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Patient Input")
    y -= 14
    pdf.setFont("Helvetica", 10)
    y = _draw_wrapped_text(pdf, f"Age: {payload.get('age')} | Gender: {payload.get('gender')} | Duration: {payload.get('symptom_duration')}", 40, y)
    y = _draw_wrapped_text(pdf, f"Additional notes: {payload.get('additional_notes', '')}", 40, y)
    y -= 10

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Question Answers")
    y -= 14
    pdf.setFont("Helvetica", 10)
    for item in payload.get("question_answers", []):
        q = item.get("question", "")
        a = item.get("answer", "")
        y = _draw_wrapped_text(pdf, f"Q: {q}", 40, y)
        y = _draw_wrapped_text(pdf, f"A: {a or '-'}", 40, y)
        y -= 6

    if y < 180:
        pdf.showPage()
        y = 810
    else:
        y -= 10

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "AI Assessment Output")
    y -= 14
    pdf.setFont("Helvetica", 10)
    _draw_wrapped_text(pdf, ai_report, 40, y)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
