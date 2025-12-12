from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from django.conf import settings
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
NAVY = colors.HexColor("#0f172a")
OUTER_BORDER = colors.HexColor("#1e3a8a")
INNER_BORDER = colors.HexColor("#b45309")
SUBTEXT = colors.HexColor("#475569")
LIGHT_TEXT = colors.Color(0.35, 0.4, 0.47, alpha=0.5)

logger = logging.getLogger(__name__)

BASE_DIR = Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parent.parent))
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_LOGO_DIR = PROJECT_ROOT / "frontend" / "src" / "logos"


def _load_logo(filename: str) -> Optional[ImageReader]:
    path = FRONTEND_LOGO_DIR / filename
    if not path.exists():
        logger.warning("Logo asset missing: %s", path)
        return None
    try:
        return ImageReader(str(path))
    except Exception as exc:  # pragma: no cover - asset loading edge cases
        logger.warning("Unable to load logo %s: %s", path, exc)
        return None


MAIN_LOGO = _load_logo("iscb-logo.png")
PARTNER_LOGO = _load_logo("sk-logo.png")
SEAL_LOGO = _load_logo("gold-seal.png")
SIGNATURE_TRAINING = _load_logo("signature.png")
SIGNATURE_EXAM = _load_logo("signature2.png")


@dataclass(slots=True)
class CertificateData:
    """Payload describing the dynamic pieces that appear on a certificate."""

    recipient_name: str
    course_title: str
    plan_label: str
    plan_type: str
    completion_date: date
    certificate_id: str
    qr_payload: str
    project_title: Optional[str] = None

    def formatted_date(self) -> str:
        return self.completion_date.strftime("%B %d, %Y")


class CertificateGenerator:
    """Utility that renders a landscape A4 certificate using ReportLab."""

    @staticmethod
    def generate_pdf(data: CertificateData, output_path: Optional[str] = None) -> bytes:
        """
        Create a certificate PDF and optionally write it to disk.

        Returns the PDF bytes so callers can attach them to HTTP responses or uploads.
        """
        buffer = BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

        CertificateGenerator._draw_background(pdf_canvas)
        CertificateGenerator._draw_header(pdf_canvas, data)
        CertificateGenerator._draw_body(pdf_canvas, data)
        CertificateGenerator._draw_footer(pdf_canvas, data)

        pdf_canvas.showPage()
        pdf_canvas.save()
        pdf_bytes = buffer.getvalue()

        if output_path:
            path = Path(output_path)
            path.write_bytes(pdf_bytes)

        return pdf_bytes

    @staticmethod
    def _draw_background(pdf_canvas: canvas.Canvas) -> None:
        pdf_canvas.setFillColor(colors.white)
        pdf_canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)

        # Outer border
        pdf_canvas.setStrokeColor(OUTER_BORDER)
        pdf_canvas.setLineWidth(36)
        pdf_canvas.rect(18, 18, PAGE_WIDTH - 36, PAGE_HEIGHT - 36, stroke=1, fill=0)

        # Inner border
        pdf_canvas.setStrokeColor(INNER_BORDER)
        pdf_canvas.setLineWidth(8)
        pdf_canvas.rect(48, 48, PAGE_WIDTH - 96, PAGE_HEIGHT - 96, stroke=1, fill=0)

        # Watermark
        pdf_canvas.saveState()
        pdf_canvas.setFillColor(LIGHT_TEXT)
        pdf_canvas.setFont("Helvetica-Bold", 160)
        pdf_canvas.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
        pdf_canvas.drawCentredString(0, -40, "CITS")
        pdf_canvas.restoreState()

    @staticmethod
    def _draw_header(pdf_canvas: canvas.Canvas, data: CertificateData) -> None:
        y = PAGE_HEIGHT - 140
        center = PAGE_WIDTH / 2

        if MAIN_LOGO:
            logo_width = 65 * mm
            logo_height = 35 * mm
            pdf_canvas.drawImage(
                MAIN_LOGO,
                center - (logo_width / 2),
                y,
                width=logo_width,
                height=logo_height,
                mask="auto",
                preserveAspectRatio=True,
            )
            y -= logo_height + 10

        pdf_canvas.setFillColor(NAVY)
        pdf_canvas.setFont("Helvetica-Bold", 20)
        pdf_canvas.drawCentredString(center, y, "Centre for Industrial Training & Skills")
        y -= 18
        pdf_canvas.setFont("Helvetica", 10)
        pdf_canvas.setFillColor(SUBTEXT)
        pdf_canvas.drawCentredString(
            center,
            y,
            "An Autonomous Quality Assessment Body | ISO 9001:2015 Compliant",
        )
        y -= 30
        pdf_canvas.setFillColor(NAVY)
        pdf_canvas.setFont("Helvetica", 11)
        pdf_canvas.drawCentredString(center, y, "THIS IS TO CERTIFY THAT")

    @staticmethod
    def _draw_body(pdf_canvas: canvas.Canvas, data: CertificateData) -> None:
        center = PAGE_WIDTH / 2
        y = PAGE_HEIGHT - 220

        # Student name
        pdf_canvas.setFillColor(NAVY)
        pdf_canvas.setFont("Times-Italic", 40)
        pdf_canvas.drawCentredString(center, y, data.recipient_name)
        y -= 32

        line_text = CertificateGenerator._plan_line(data.plan_type)
        pdf_canvas.setFont("Helvetica", 14)
        pdf_canvas.setFillColor(NAVY)
        pdf_canvas.drawCentredString(center, y, line_text)
        y -= 26

        pdf_canvas.setFont("Helvetica-Bold", 22)
        pdf_canvas.drawCentredString(center, y, data.course_title.upper())
        y -= 36

        paragraph = CertificateGenerator._plan_paragraph(
            data.plan_type,
            data.project_title,
        )
        pdf_canvas.setFont("Helvetica", 12)
        pdf_canvas.setFillColor(SUBTEXT)
        for line in simpleSplit(paragraph, "Helvetica", 12, PAGE_WIDTH - 160):
            pdf_canvas.drawCentredString(center, y, line)
            y -= 16

        y -= 10
        pdf_canvas.setFont("Helvetica-Bold", 11)
        pdf_canvas.setFillColor(NAVY)
        pdf_canvas.drawCentredString(
            center,
            y,
            f"Plan: {data.plan_label} • Issued on {data.formatted_date()}",
        )

    @staticmethod
    def _draw_footer(pdf_canvas: canvas.Canvas, data: CertificateData) -> None:
        margin = 80
        col_width = (PAGE_WIDTH - (2 * margin)) / 3
        base_y = 120

        # Training partner block
        x = margin
        pdf_canvas.setFillColor(SUBTEXT)
        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.drawString(x, base_y + 100, "TRAINING PARTNER")

        if PARTNER_LOGO:
            pdf_canvas.drawImage(
                PARTNER_LOGO,
                x,
                base_y + 40,
                width=55 * mm,
                height=25 * mm,
                mask="auto",
                preserveAspectRatio=True,
            )
        pdf_canvas.setFillColor(NAVY)
        pdf_canvas.setFont("Helvetica-Bold", 12)
        pdf_canvas.drawString(x, base_y + 30, "CITS Digital Lab")
        pdf_canvas.setFillColor(SUBTEXT)
        pdf_canvas.setFont("Helvetica", 9)
        pdf_canvas.drawString(x, base_y + 15, "Govt. Regd. MSME")

        if SIGNATURE_TRAINING:
            pdf_canvas.drawImage(
                SIGNATURE_TRAINING,
                x,
                base_y - 10,
                width=45 * mm,
                height=15 * mm,
                mask="auto",
                preserveAspectRatio=True,
            )
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.drawString(x, base_y - 20, "Director, CITS Digital Lab")

        # Seal + certificate details
        x = margin + col_width
        if SEAL_LOGO:
            pdf_canvas.drawImage(
                SEAL_LOGO,
                x + (col_width - (45 * mm)) / 2,
                base_y + 10,
                width=45 * mm,
                height=35 * mm,
                mask="auto",
                preserveAspectRatio=True,
            )
        pdf_canvas.setFillColor(SUBTEXT)
        pdf_canvas.setFont("Helvetica-Bold", 9)
        pdf_canvas.drawCentredString(x + col_width / 2, base_y - 5, "Certificate ID")
        pdf_canvas.setFillColor(NAVY)
        pdf_canvas.setFont("Helvetica-Bold", 12)
        pdf_canvas.drawCentredString(x + col_width / 2, base_y - 20, data.certificate_id)
        pdf_canvas.setFillColor(SUBTEXT)
        pdf_canvas.setFont("Helvetica", 9)
        pdf_canvas.drawCentredString(
            x + col_width / 2,
            base_y - 35,
            f"Awarded on {data.formatted_date()}",
        )

        # Examination block with QR
        x = margin + (2 * col_width)
        pdf_canvas.setFillColor(SUBTEXT)
        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.drawRightString(x + col_width, base_y + 100, "EXAMINATION CONTROLLER")

        qr_image = CertificateGenerator._build_qr_image(data.qr_payload)
        if qr_image:
            pdf_canvas.drawImage(
                qr_image,
                x + col_width - (30 * mm),
                base_y + 30,
                width=30 * mm,
                height=30 * mm,
            )
        else:
            pdf_canvas.rect(
                x + col_width - (30 * mm),
                base_y + 30,
                30 * mm,
                30 * mm,
                stroke=1,
                fill=0,
            )
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.drawRightString(x + col_width, base_y + 25, "Scan to verify")

        if SIGNATURE_EXAM:
            pdf_canvas.drawImage(
                SIGNATURE_EXAM,
                x + col_width - (45 * mm),
                base_y - 5,
                width=45 * mm,
                height=15 * mm,
                mask="auto",
                preserveAspectRatio=True,
            )
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.drawRightString(x + col_width, base_y - 20, "Controller of Exams, CITS")

    @staticmethod
    def _build_qr_image(payload: str) -> Optional[ImageReader]:
        if not payload:
            return None
        qr = qrcode.QRCode(version=2, box_size=10, border=1)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return ImageReader(buffer)

    @staticmethod
    def _plan_line(plan_type: str) -> str:
        plan_type = (plan_type or "").lower()
        if plan_type == "industrial":
            return "has successfully completed the 3-Month Virtual Industrial Training Program in"
        if plan_type == "mastery":
            return "has demonstrated expert-level proficiency and is hereby awarded this Master Certification in"
        return "has successfully completed the competence requirement for"

    @staticmethod
    def _plan_paragraph(plan_type: str, project_title: Optional[str]) -> str:
        plan_type = (plan_type or "").lower()
        if plan_type == "industrial":
            project_segment = (
                f" titled: \"{project_title}\"." if project_title else "."
            )
            return (
                "The candidate has demonstrated proficiency in practical application, adherence to industry standards, "
                f"and successful execution of the required capstone project{project_segment} "
                "This certification validates 120 hours of competency-based learning and project implementation."
            )
        if plan_type == "mastery":
            return (
                "The candidate has successfully met the rigorous assessment benchmarks set by the Examination Board. "
                "This credential attests to advanced mastery in core frameworks, specialized tools, and industrial "
                "deployment methodologies, equivalent to a 6-month (240 hours) professional specialization track."
            )
        return (
            "The candidate has demonstrated fundamental understanding and working knowledge of the subject matter, "
            "adhering to the evaluation standards set by the Centre for Industrial Training & Skills (CITS)."
        )


def _demo() -> None:
    """Generate a sample certificate for local testing."""

    sample_data = CertificateData(
        recipient_name="Aarav Kapoor",
        course_title="AI & Data Automation",
        plan_label="Industrial Training",
        plan_type="industrial",
        completion_date=datetime.utcnow().date(),
        certificate_id="CERT-2024-0001",
        qr_payload="https://example.com/verify/CERT-2024-0001",
        project_title="Predictive Maintenance Platform",
    )
    output_file = Path(__file__).resolve().parent.parent / "sample_certificate.pdf"
    CertificateGenerator.generate_pdf(sample_data, output_path=str(output_file))
    print(f"Sample certificate written to {output_file}")


if __name__ == "__main__":
    _demo()

    @staticmethod
    def _plan_line(plan_type: str) -> str:
        plan_type = (plan_type or "").lower()
        if plan_type == "industrial":
            return "has successfully completed the 3-Month Virtual Industrial Training Program in"
        if plan_type == "mastery":
            return "has demonstrated expert-level proficiency and is hereby awarded this Master Certification in"
        return "has successfully completed the competence requirement for"

    @staticmethod
    def _plan_paragraph(plan_type: str, project_title: Optional[str]) -> str:
        plan_type = (plan_type or "").lower()
        if plan_type == "industrial":
            project_segment = (
                f" titled: \"{project_title}\"." if project_title else "."
            )
            return (
                "The candidate has demonstrated proficiency in practical application, adherence to industry standards, "
                f"and successful execution of the required capstone project{project_segment} "
                "This certification validates 120 hours of competency-based learning and project implementation."
            )
        if plan_type == "mastery":
            return (
                "The candidate has successfully met the rigorous assessment benchmarks set by the Examination Board. "
                "This credential attests to advanced mastery in core frameworks, specialized tools, and industrial "
                "deployment methodologies, equivalent to a 6-month (240 hours) professional specialization track."
            )
        return (
            "The candidate has demonstrated fundamental understanding and working knowledge of the subject matter, "
            "adhering to the evaluation standards set by the Centre for Industrial Training & Skills (CITS)."
        )


def _demo() -> None:
    """Generate a sample certificate for local testing."""

    sample_data = CertificateData(
        recipient_name="Aarav Kapoor",
        course_title="AI & Data Automation",
        plan_label="Industrial Training",
        plan_type="industrial",
        completion_date=datetime.utcnow().date(),
        certificate_id="CERT-2024-0001",
        qr_payload="https://example.com/verify/CERT-2024-0001",
        project_title="Predictive Maintenance Platform",
    )
    output_file = Path(__file__).resolve().parent.parent / "sample_certificate.pdf"
    CertificateGenerator.generate_pdf(sample_data, output_path=str(output_file))
    print(f"Sample certificate written to {output_file}")


if __name__ == "__main__":
    _demo()



