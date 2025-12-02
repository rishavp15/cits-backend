"""
Service to render React certificate templates as PDF using Playwright.
"""
import base64
import logging
from io import BytesIO
from typing import Optional
from urllib.parse import quote

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. PDF rendering will not work.")

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    logger.warning("qrcode library not installed. QR codes will not be generated.")


class PDFRenderError(Exception):
    """Raised when PDF rendering fails."""


def render_certificate_pdf(
    certificate_id: str,
    student_name: str,
    course_name: str,
    plan_type: str,
    award_date: str,
    qr_payload: str,
    project_title: Optional[str] = None,
    duration: Optional[str] = None,
) -> bytes:
    """
    Render a React certificate as PDF by visiting the certificate URL and generating PDF.
    
    Args:
        certificate_id: Certificate ID
        student_name: Student's name
        course_name: Course name
        plan_type: Plan type (basic, industrial, mastery)
        award_date: Award date string
        qr_payload: QR code payload (URL to encode in QR code)
        project_title: Optional project title (for industrial/mastery)
        duration: Optional duration string
        
    Returns:
        PDF bytes
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise PDFRenderError("Playwright is not installed. Please install it: pip install playwright && playwright install chromium")
    
    frontend_url = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")
    
    # Build certificate URL with query parameters
    params = {
        "certificateId": certificate_id,
        "studentName": student_name,
        "courseName": course_name,
        "planType": plan_type,
        "awardDate": award_date,
        "qrPayload": qr_payload,
    }
    if project_title:
        params["projectTitle"] = project_title
    if duration:
        params["duration"] = duration
    
    # Create certificate preview URL (URL encode all params)
    query_string = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
    certificate_url = f"{frontend_url}/certificate/pdf?{query_string}"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set viewport to A4 size (landscape for certificates)
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate to certificate page
            page.goto(certificate_url, wait_until="networkidle", timeout=30000)
            
            # Wait for certificate to render (look for certificate element)
            try:
                page.wait_for_selector(".certificate-sheet, .certificate-standalone", timeout=10000)
            except Exception:
                logger.warning("Certificate element not found, proceeding anyway")
            
            # Generate PDF
            pdf_bytes = page.pdf(
                format="A4",
                landscape=True,
                print_background=True,
                margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
            )
            
            browser.close()
            return pdf_bytes
            
    except Exception as exc:
        logger.exception("Failed to render certificate PDF: %s", exc)
        raise PDFRenderError(f"Failed to render PDF: {str(exc)}") from exc


"""
import base64
import logging
from io import BytesIO
from typing import Optional
from urllib.parse import quote

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. PDF rendering will not work.")

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    logger.warning("qrcode library not installed. QR codes will not be generated.")


class PDFRenderError(Exception):
    """Raised when PDF rendering fails."""


def render_certificate_pdf(
    certificate_id: str,
    student_name: str,
    course_name: str,
    plan_type: str,
    award_date: str,
    qr_payload: str,
    project_title: Optional[str] = None,
    duration: Optional[str] = None,
) -> bytes:
    """
    Render a React certificate as PDF by visiting the certificate URL and generating PDF.
    
    Args:
        certificate_id: Certificate ID
        student_name: Student's name
        course_name: Course name
        plan_type: Plan type (basic, industrial, mastery)
        award_date: Award date string
        qr_payload: QR code payload (URL to encode in QR code)
        project_title: Optional project title (for industrial/mastery)
        duration: Optional duration string
        
    Returns:
        PDF bytes
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise PDFRenderError("Playwright is not installed. Please install it: pip install playwright && playwright install chromium")
    
    frontend_url = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")
    
    # Build certificate URL with query parameters
    params = {
        "certificateId": certificate_id,
        "studentName": student_name,
        "courseName": course_name,
        "planType": plan_type,
        "awardDate": award_date,
        "qrPayload": qr_payload,
    }
    if project_title:
        params["projectTitle"] = project_title
    if duration:
        params["duration"] = duration
    
    # Create certificate preview URL (URL encode all params)
    query_string = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
    certificate_url = f"{frontend_url}/certificate/pdf?{query_string}"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set viewport to A4 size (landscape for certificates)
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate to certificate page
            page.goto(certificate_url, wait_until="networkidle", timeout=30000)
            
            # Wait for certificate to render (look for certificate element)
            try:
                page.wait_for_selector(".certificate-sheet, .certificate-standalone", timeout=10000)
            except Exception:
                logger.warning("Certificate element not found, proceeding anyway")
            
            # Generate PDF
            pdf_bytes = page.pdf(
                format="A4",
                landscape=True,
                print_background=True,
                margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
            )
            
            browser.close()
            return pdf_bytes
            
    except Exception as exc:
        logger.exception("Failed to render certificate PDF: %s", exc)
        raise PDFRenderError(f"Failed to render PDF: {str(exc)}") from exc

