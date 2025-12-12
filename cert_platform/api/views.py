import json
import logging
import random
import uuid
import base64
import hashlib
import os
import time
import threading
from datetime import date, datetime, timedelta
from typing import Optional

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import (
    require_GET,
    require_POST,
    require_http_methods,
)

from .models import (
    Assessment,
    AssessmentAttempt,
    Certificate,
    CertificateDeliveryLog,
    ContactMessage,
    Course,
    EmailOTP,
    Payment,
)
from .services.gmail import GmailSendError, send_certificate_email
from .certificates import CertificateData, CertificateGenerator

import requests
import base64
import hashlib
import os
import time


logger = logging.getLogger(__name__)

# In-memory token cache for PhonePe auth (simple, per-process)
PHONEPE_TOKEN_CACHE = {
    "token": None,
    "expires_at": 0,
}


PASS_THRESHOLD = 0.4

FALLBACK_QUESTIONS = [
    {
        "id": 1,
        "question": "Which library is primarily used for data manipulation in Python?",
        "options": ["React", "Pandas", "Vue", "Laravel"],
        "answer": "Pandas",
    },
    {
        "id": 2,
        "question": "What does CSV stand for?",
        "options": [
            "Computer Style View",
            "Comma Separated Values",
            "Code Syntax Variable",
            "None",
        ],
        "answer": "Comma Separated Values",
    },
    {
        "id": 3,
        "question": "Which metric is commonly used to evaluate a classification model?",
        "options": ["Mean Squared Error", "R-Squared", "Accuracy", "Variance"],
        "answer": "Accuracy",
    },
    {
        "id": 4,
        "question": "What is the purpose of the 'head()' function in Pandas?",
        "options": [
            "Delete the first row",
            "Return the last 5 rows",
            "Return the first n rows",
            "Calculate the mean",
        ],
        "answer": "Return the first n rows",
    },
    {
        "id": 5,
        "question": "Which of the following is a supervised learning algorithm?",
        "options": [
            "K-Means Clustering",
            "Linear Regression",
            "Apriori",
            "DBSCAN",
        ],
        "answer": "Linear Regression",
    },
]

SYLLABUS = [
    {
        "title": "Month 1: Fundamentals",
        "source": "Harvard CS50 Adaptation",
        "topics": ["Python Basics", "Statistics", "Algorithms"],
    },
    {
        "title": "Month 2: Analysis",
        "source": "Microsoft Excel & PowerBI",
        "topics": ["Pivot Tables", "Dashboards", "Data Cleaning"],
    },
    {
        "title": "Month 3: AI Implementation",
        "source": "Google TensorFlow",
        "topics": ["Neural Networks", "Deep Learning", "Model Deployment"],
    },
]

PLAN_RULES = {
    "basic": {
        "label": "Basic",
        "price": 499,
        "original_price": 799,
        "currency": "INR",
        "requires_project": False,
        "description": "Skill Validation - PDF only",
        "duration_days": 0,
    },
    "industrial": {
        "label": "Industrial Training",
        "price": 999,
        "original_price": 1499,
        "currency": "INR",
        "requires_project": True,
        "description": "Industrial Training (3 Months)",
        "duration_days": 90,
    },
    "mastery": {
        "label": "Mastery Certification",
        "price": 1499,
        "original_price": 2199,
        "currency": "INR",
        "requires_project": True,
        "description": "Mastery Diploma (6 Months)",
        "max_duration_days": 180,
    },
}

PLAN_SIZE_METADATA = {
    "basic": {"size": "small", "display": "Small Certificate (₹499)"},
    "industrial": {"size": "medium", "display": "Medium Certificate (₹999)"},
    "mastery": {"size": "large", "display": "Large Diploma (₹1,499)"},
}

FRONTEND_BASE_URL = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")
VERIFY_PAGE_URL = f"{FRONTEND_BASE_URL.rstrip('/')}/verify"

CERTIFICATE_PREVIEWS = {
    "horizontal": "https://dummyimage.com/600x400/0f172a/ffffff.png&text=Horizontal+Preview",
    "vertical": "https://dummyimage.com/480x640/0f172a/ffffff.png&text=Vertical+Preview",
}

ADMIN_TOKEN_TTL_SECONDS = getattr(settings, "ADMIN_TOKEN_TTL_SECONDS", 60 * 60 * 12)


def _json_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def _parse_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload") from exc


def _is_email_verified(email: str) -> bool:
    if not email:
        return False
    cutoff = timezone.now() - timedelta(minutes=30)
    return EmailOTP.objects.filter(email__iexact=email, verified_at__gte=cutoff).exists()


def _serialize_course(course: Course):
    # Safely get assessment
    assessment_slug = None
    try:
        assessment = course.assessments.filter(is_active=True).first()
        if assessment:
            assessment_slug = assessment.slug
    except Exception:
        pass  # If relationship doesn't exist or fails, just use None
    
    # Safely get JSON fields, defaulting to empty list/dict if None or invalid
    def safe_json_field(field_value, default):
        if field_value is None:
            return default
        if isinstance(field_value, (list, dict, str, int, float, bool)):
            # Django JSONField already returns Python objects, so just return them
            if isinstance(field_value, (list, dict)):
                # Ensure all nested values are JSON-serializable
                try:
                    json.dumps(field_value)
                    return field_value
                except (TypeError, ValueError):
                    return default
            return field_value
        try:
            if isinstance(field_value, str):
                parsed = json.loads(field_value)
                return parsed
            return default
        except (json.JSONDecodeError, TypeError, ValueError):
            return default
    
    return {
        "slug": str(course.slug) if course.slug else "",
        "title": str(course.title) if course.title else "",
        "description": str(course.description) if course.description else "",
        # SEO metadata (optional; frontend can fall back to title/description)
        "seoTitle": str(course.seo_title) if getattr(course, "seo_title", None) else "",
        "seoDescription": str(course.seo_description) if getattr(course, "seo_description", None) else "",
        "seoKeywords": str(course.seo_keywords) if getattr(course, "seo_keywords", None) else "",
        "ogImageUrl": str(course.og_image_url) if getattr(course, "og_image_url", None) else "",
        "heroTagline": str(course.hero_tagline) if course.hero_tagline else "",
        "heroTitle": str(course.hero_title) if course.hero_title else "",
        "heroDescription": str(course.hero_description) if course.hero_description else "",
        "heroImageUrl": str(course.hero_image_url) if course.hero_image_url else "",
        "cardImageUrl": str(course.card_image_url) if course.card_image_url else "",
        "galleryImages": safe_json_field(course.gallery_images, []),
        "trustGrid": safe_json_field(course.trust_grid, []),
        "certifications": safe_json_field(course.certifications, []),
        "testimonials": safe_json_field(course.testimonials, []),
        "subject": str(course.subject) if course.subject else "",
        "icon": str(course.icon) if course.icon else "",
        "color": str(course.color) if course.color else "",
        "students": int(course.students) if course.students else 0,
        "durationHours": int(course.duration_hours) if course.duration_hours else 0,
        "logoUrl": str(course.logo_url) if course.logo_url else "",
        "syllabus": safe_json_field(course.syllabus, []),
        "classLinks": safe_json_field(course.class_links, []),
        "competencies": safe_json_field(course.competencies, []),
        "planHighlights": safe_json_field(course.plan_highlights, {}),
        "certificateTypes": safe_json_field(course.certificate_types, []),
        "openStandardsLabel": str(course.open_standards_label) if course.open_standards_label else "",
        "playlistModules": safe_json_field(course.playlist_modules, []),
        "projectTitleSuggestions": safe_json_field(getattr(course, "project_title_suggestions", None), []),
        "assessmentSlug": str(assessment_slug) if assessment_slug else None,
    }


def _get_plan_policy(plan_key: str):
    from .models import PlanConfig

    base = PLAN_RULES.get(plan_key)
    if not base:
        return None

    config = (
        PlanConfig.objects.filter(plan_type=plan_key, is_active=True)
        .order_by("-updated_at")
        .first()
    )
    if not config:
        return base

    policy = {**base}
    policy["price"] = float(config.price)
    if config.original_price is not None:
        policy["original_price"] = float(config.original_price)
    if config.label_override:
        policy["label"] = config.label_override
    if config.currency:
        policy["currency"] = config.currency
    return policy


def _serialize_plan(key, policy):
    preview = CERTIFICATE_PREVIEWS.get("horizontal")
    original_price = policy.get("original_price")
    price = policy["price"]
    discount_percent = None
    if original_price and original_price > price:
        discount_percent = round(100 - (price / original_price * 100))
    return {
        "key": key,
        "label": policy["label"],
        "price": price,
        "originalPrice": original_price,
        "discountPercent": discount_percent,
        "currency": policy.get("currency", "INR"),
        "requiresProject": policy["requires_project"],
        "description": policy["description"],
        "durationDays": policy.get("duration_days"),
        "maxDurationDays": policy.get("max_duration_days"),
        "defaultPreview": preview,
    }


def _get_assessment(course_slug: Optional[str], assessment_slug: Optional[str]):
    query = Assessment.objects.filter(is_active=True).select_related("course")
    if assessment_slug:
        return query.filter(slug=assessment_slug).first()
    if course_slug:
        return query.filter(course__slug=course_slug).first()
    return query.first()


def _sanitize_questions(questions):
    sanitized = []
    for question in questions:
        sanitized.append(
            {
                "id": question["id"] if isinstance(question, dict) else question.id,
                "question": question["question"] if isinstance(question, dict) else question.prompt,
                "options": question["options"] if isinstance(question, dict) else question.options,
            }
        )
    return sanitized


def _make_certificate_id():
    return f"CERT-{uuid.uuid4().hex[:10].upper()}"


def _issue_certificate(payment: Payment, note: str):
    certificate = Certificate.objects.create(
        certificate_id=_make_certificate_id(),
        email=payment.email,
        plan_type=payment.plan_type,
        course=payment.course,
        orientation=payment.certificate_orientation,
        status="issued",
        payment=payment,
    )
    CertificateDeliveryLog.objects.create(
        certificate=certificate,
        status="pending",
        detail={"note": note},
    )
    return certificate


def _schedule_certificate_email(
    *,
    certificate: Certificate,
    payment: Payment,
    course_title: str,
    plan_label: str,
    verify_url: str,
    download_url: str,
    delay_seconds: int = 240,
):
    """
    Send the certificate email after a short delay (default 4 minutes).
    """

    def _send():
        email_body = (
            f"Dear {payment.name},\n\n"
            f"Congratulations! Your CITS Digital credential has been issued.\n\n"
            f"Certificate ID: {certificate.certificate_id}\n"
            f"Course: {course_title}\n"
            f"Plan: {plan_label}\n\n"
            f"You can verify your certificate at:\n{verify_url}\n\n"
            f"You can download your certificate PDF from:\n{download_url}\n\n"
            f"If you need any support help, call us at +91-9113750231.\n\n"
            f"If you did not request this credential, please contact support immediately.\n\n"
            f"Regards,\nCITS Digital Certification Desk"
        )
        try:
            send_certificate_email(
                recipient=payment.email,
                subject="Your CITS Digital Certificate",
                body=email_body,
            )
            CertificateDeliveryLog.objects.create(
                certificate=certificate,
                status="sent",
                detail={"trigger": "auto-issue-delayed"},
            )
        except GmailSendError as exc:
            CertificateDeliveryLog.objects.create(
                certificate=certificate,
                status="failed",
                detail={"trigger": "auto-issue-delayed", "reason": str(exc)},
            )

    timer = threading.Timer(delay_seconds, _send)
    timer.daemon = True
    timer.start()


def _ensure_certificate(payment: Payment, desired_id: Optional[str] = None):
    certificate = payment.certificates.filter(plan_type=payment.plan_type).first()
    normalized_id = desired_id.strip().upper() if desired_id else None

    if certificate:
        if normalized_id and certificate.certificate_id != normalized_id:
            if Certificate.objects.exclude(pk=certificate.pk).filter(certificate_id__iexact=normalized_id).exists():
                raise ValueError("Certificate ID already in use.")
            certificate.certificate_id = normalized_id
            certificate.save(update_fields=["certificate_id", "updated_at"])
        return certificate

    certificate_id = normalized_id or _make_certificate_id()
    if Certificate.objects.filter(certificate_id__iexact=certificate_id).exists():
        certificate_id = _make_certificate_id()

    return Certificate.objects.create(
        certificate_id=certificate_id,
        email=payment.email,
        plan_type=payment.plan_type,
        course=payment.course,
        orientation=payment.certificate_orientation,
        status="issued",
        payment=payment,
    )


def _validate_admin_request(request):
    token = request.headers.get("X-Admin-Auth") or request.META.get("HTTP_X_ADMIN_AUTH")
    if not token:
        return _json_error("Unauthorized", status=401)
    signer = signing.TimestampSigner(settings.SECRET_KEY)
    try:
        value = signer.unsign(token, max_age=ADMIN_TOKEN_TTL_SECONDS)
    except signing.BadSignature:
        return _json_error("Unauthorized", status=401)
    if value != "admin":
        return _json_error("Unauthorized", status=401)
    return None


@require_GET
def health_check(_request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "cert_platform_api",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )


@require_GET
def get_syllabus(_request):
    return JsonResponse({"syllabus": SYLLABUS})


@require_GET
def list_questions(request):
    course_slug = request.GET.get("course")
    assessment_slug = request.GET.get("assessment")
    assessment = _get_assessment(course_slug, assessment_slug)

    if assessment and assessment.questions.exists():
        questions = [
            {
                "id": question.id,
                "question": question.prompt,
                "options": question.options,
            }
            for question in assessment.questions.all()
        ]
        pass_score = float(assessment.pass_threshold)
        duration = assessment.duration_minutes
    else:
        questions = _sanitize_questions(FALLBACK_QUESTIONS)
        pass_score = PASS_THRESHOLD * 100
        duration = 15

    return JsonResponse(
        {
            "questions": questions,
            "timeLimitMinutes": duration,
            "passingScorePercent": pass_score,
            "courseSlug": assessment.course.slug if assessment else course_slug,
            "assessmentSlug": assessment.slug if assessment else assessment_slug,
        }
    )


@csrf_exempt
@require_GET
def list_courses(_request):
    try:
        courses = Course.objects.all().order_by("title").prefetch_related("assessments")
        data = []
        for course in courses:
            try:
                serialized = _serialize_course(course)
                # Verify it's JSON-serializable before adding
                json.dumps(serialized)
                data.append(serialized)
            except Exception as exc:
                logger.exception("Error serializing course %s: %s", getattr(course, 'slug', 'unknown'), exc)
                # Skip this course if serialization fails
                continue
        fallback = [
            {
                "slug": "data-science",
                "title": "Data Science & AI",
                "description": "Comprehensive curriculum covering Statistics, Python, Deep Learning, and Industrial Analytics.",
            }
        ]
        return JsonResponse({"courses": data or fallback}, safe=False)
    except Exception as exc:
        logger.exception("Error in list_courses: %s", exc)
        return _json_error(f"Failed to fetch courses: {str(exc)}", status=500)


@require_GET
def list_assessments(request):
    course_slug = request.GET.get("course")
    query = Assessment.objects.filter(is_active=True).select_related("course").prefetch_related("questions")
    if course_slug:
        query = query.filter(course__slug=course_slug)
    data = [
        {
            "slug": assessment.slug,
            "courseSlug": assessment.course.slug if assessment.course else None,
            "courseTitle": assessment.course.title if assessment.course else None,
            "title": assessment.title,
            "durationMinutes": assessment.duration_minutes,
            "passThreshold": float(assessment.pass_threshold),
            "instructions": assessment.instructions,
            "questionCount": assessment.questions.count(),
        }
        for assessment in query
    ]
    return JsonResponse({"assessments": data})


@csrf_exempt
@require_POST
def submit_assessment(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    responses = payload.get("responses")
    if not isinstance(responses, list) or not responses:
        return _json_error("Responses list is required.")

    course_slug = payload.get("courseSlug")
    assessment_slug = payload.get("assessmentSlug")
    assessment = _get_assessment(course_slug, assessment_slug)

    if assessment and assessment.questions.exists():
        question_map = {question.id: question for question in assessment.questions.all()}
        threshold = float(assessment.pass_threshold)
    else:
        question_map = {question["id"]: question for question in FALLBACK_QUESTIONS}
        threshold = PASS_THRESHOLD * 100

    total_questions = len(question_map)
    if total_questions == 0:
        return _json_error("Assessment is not ready. Please try later.", status=503)

    correct_count = 0
    for item in responses:
        question = question_map.get(item.get("id"))
        if not question:
            continue
        answer = item.get("answer")
        correct_answer = (
            question.answer if hasattr(question, "answer") else question["answer"]
        )
        if answer == correct_answer:
            correct_count += 1

    percentage = (correct_count / total_questions) * 100
    passed = percentage >= threshold

    if assessment:
        AssessmentAttempt.objects.create(
            assessment=assessment,
            email=payload.get("email", ""),
            score_percent=percentage,
            passed=passed,
            responses=responses,
            correct_count=correct_count,
            total_questions=total_questions,
        )

    return JsonResponse(
        {
            "correct": correct_count,
            "total": total_questions,
            "percentage": round(percentage, 2),
            "passed": passed,
            "nextRoute": "/results" if passed else "/assessment",
            "courseSlug": course_slug or (assessment.course.slug if assessment else None),
            "assessmentSlug": assessment.slug if assessment else None,
        }
    )


def _parse_date(value: Optional[str]):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@csrf_exempt
@require_POST
def checkout_plan(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    try:
        plan_key = (payload.get("planType") or "").lower()
        declaration = payload.get("declarationAccepted")
        policy = _get_plan_policy(plan_key)

        if not policy:
            return _json_error("Invalid plan selected.")
        required_fields = ["name", "email", "phone", "collegeName", "semester"]
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            return _json_error(f"Missing required fields: {', '.join(missing)}")
        if declaration is not True:
            return _json_error("Self-declaration must be accepted.")

        email = (payload.get("email") or "").strip()
        # In test mode we auto-verify; _is_email_verified returns True
        course = Course.objects.filter(slug=payload.get("courseSlug")).first()
        assessment = _get_assessment(payload.get("courseSlug"), payload.get("assessmentSlug"))

        project_link = payload.get("projectLink") or payload.get("repositoryLink")
        project_description = payload.get("projectDescription", "")
        project_title = payload.get("projectTitle", "")
        project_archive_name = payload.get("projectArchiveName")
        project_archive_data = payload.get("projectArchiveData")
        if policy["requires_project"] and not project_link:
            return _json_error("Project or repository link is required for this plan.")

        orientation = payload.get("orientation", "horizontal").lower()
        if orientation not in dict(Payment.ORIENTATION_CHOICES):
            return _json_error("Invalid certificate orientation.")

        # Automatically assign plan duration windows without asking the student
        start_date = None
        end_date = None

        if plan_key == "industrial":
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=policy["duration_days"])
        elif plan_key == "mastery":
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=policy["max_duration_days"])

        transaction_id = f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        archive_payload = None
        if project_archive_name or project_archive_data:
            archive_payload = {
                "name": project_archive_name,
                "size": len(project_archive_data or ""),
                "data": project_archive_data,
            }

        payment = Payment.objects.create(
            transaction_id=transaction_id,
            course=course,
            assessment=assessment,
            plan_type=plan_key,
            name=payload["name"],
            email=email,
            phone=payload["phone"],
            amount=policy["price"],
            currency=policy.get("currency", "INR"),
            college_name=payload["collegeName"],
            semester=payload["semester"],
            project_link=payload.get("projectLink", ""),
            repository_link=payload.get("repositoryLink", ""),
            certificate_orientation=orientation,
            start_date=start_date,
            end_date=end_date,
            metadata={
                "courseSlug": payload.get("courseSlug"),
                "assessmentSlug": payload.get("assessmentSlug"),
                "certificatePreview": CERTIFICATE_PREVIEWS.get(orientation),
                "projectDescription": project_description,
                "projectTitle": project_title,
                "projectArchive": archive_payload,
            },
        )
        # ------------------------------------------------------------------
        # PhonePe Standard Checkout via REST
        # ------------------------------------------------------------------
        frontend_base_url = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")
        amount_paise = int(policy["price"]) * 100

        phonepe_payment = None
        merchant_order_id = transaction_id
        phonepe_env = (getattr(settings, "PHONEPE_ENVIRONMENT", "SANDBOX") or "SANDBOX").upper()
        is_prod = phonepe_env == "PRODUCTION"
        base_url_token = os.environ.get(
            "PHONEPE_AUTH_BASE_URL",
            "https://api.phonepe.com/apis/identity-manager" if is_prod else "https://api-preprod.phonepe.com/apis/pg-sandbox",
        )
        base_url_pg = os.environ.get(
            "PHONEPE_PG_BASE_URL",
            "https://api.phonepe.com/apis/pg" if is_prod else "https://api-preprod.phonepe.com/apis/pg-sandbox",
        )
        client_id = os.environ.get("PHONEPE_CLIENT_ID") or getattr(settings, "PHONEPE_CLIENT_ID", None)
        client_secret = os.environ.get("PHONEPE_CLIENT_SECRET") or getattr(settings, "PHONEPE_CLIENT_SECRET", None)
        client_version = int(os.environ.get("PHONEPE_CLIENT_VERSION") or 1)

        def _fetch_phonepe_token() -> Optional[str]:
            now = int(time.time())
            if PHONEPE_TOKEN_CACHE["token"] and PHONEPE_TOKEN_CACHE["expires_at"] > now + 30:
                return PHONEPE_TOKEN_CACHE["token"]
            token_url = f"{base_url_token}/v1/oauth/token"
            data = {
                "client_id": client_id,
                "client_version": client_version,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            }
            try:
                resp = requests.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10,
                )
                resp.raise_for_status()
                resp_json = resp.json()
                token = resp_json.get("access_token")
                expires_at = int(resp_json.get("expires_at") or 0)
                if token:
                    PHONEPE_TOKEN_CACHE["token"] = token
                    PHONEPE_TOKEN_CACHE["expires_at"] = expires_at
                    return token
                logger.error("PhonePe auth token missing in response: %s", resp_json)
            except Exception as exc:
                try:
                    logger.error("PhonePe auth token fetch failed (%s): %s", token_url, getattr(exc, "response", None).text if hasattr(exc, "response") and exc.response is not None else str(exc))
                except Exception:
                    logger.exception("Failed to fetch PhonePe auth token: %s", exc)
            return None

        if client_id and client_secret:
            token = _fetch_phonepe_token()
            if not token:
                logger.error("PhonePe token fetch returned None")
                return _json_error("Unable to initiate payment. Please try again.")

            pay_url = f"{base_url_pg}/checkout/v2/pay"
            redirect_url = f"{frontend_base_url}/payment-success"
            payload_body = {
                "merchantOrderId": merchant_order_id,
                "amount": amount_paise,
                "paymentFlow": {
                    "type": "PG_CHECKOUT",
                    "merchantUrls": {
                        "redirectUrl": redirect_url,
                    },
                },
                "metaInfo": {
                    "udf1": payload.get("courseSlug") or "",
                    "udf2": plan_key,
                    "udf3": email,
                },
            }
            try:
                resp = requests.post(
                    pay_url,
                    json=payload_body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"O-Bearer {token}",
                    },
                    timeout=10,
                )
                status_code = resp.status_code
                resp_text = resp.text
                resp_json = {}
                try:
                    resp_json = resp.json()
                except Exception:
                    pass

                if status_code >= 400:
                    logger.error(
                        "PhonePe pay HTTP %s for %s: %s",
                        status_code,
                        merchant_order_id,
                        resp_text,
                    )
                    msg = resp_json.get("message") or "Unable to initiate payment. Please try again."
                    return _json_error(msg)

                redirect_url_phonepe = resp_json.get("redirectUrl")
                if redirect_url_phonepe:
                    phonepe_payment = {
                        "redirectUrl": redirect_url_phonepe,
                        "orderId": resp_json.get("orderId"),
                        "state": resp_json.get("state"),
                    }
                    meta = dict(payment.metadata or {})
                    meta["phonepe"] = {
                        "merchant_order_id": merchant_order_id,
                        "amount": amount_paise,
                        "currency": policy.get("currency", "INR"),
                        "redirect_url": redirect_url,
                        "redirect_url_phonepe": redirect_url_phonepe,
                        "order_id": resp_json.get("orderId"),
                        "state": resp_json.get("state"),
                    }
                    payment.metadata = meta
                    payment.save(update_fields=["metadata", "updated_at"])
                else:
                    logger.error("PhonePe pay missing redirectUrl for %s: %s", merchant_order_id, resp_json)
                    return _json_error("Unable to initiate payment. Please try again.")
            except Exception as exc:
                try:
                    logger.error(
                        "PhonePe pay exception for %s: %s",
                        merchant_order_id,
                        getattr(exc, "response", None).text if hasattr(exc, "response") and exc.response is not None else str(exc),
                    )
                except Exception:
                    logger.exception("Failed to create PhonePe payment via REST for %s", merchant_order_id)
                return _json_error("Unable to initiate payment. Please try again in a moment.")
        else:
            logger.warning("PhonePe REST credentials not configured; skipping live payment flow.")

        response_payload = {
            "transactionId": transaction_id,
            "paymentStatus": payment.status,
            "plan": policy,
            "planType": plan_key,
            "email": payment.email,
            "amount": policy["price"],
            "redirectRoute": "/fulfillment",
            "processingTimeMs": 2000,
            "certificatePreview": CERTIFICATE_PREVIEWS.get(orientation),
            "startDate": start_date.isoformat() if start_date else None,
            "endDate": end_date.isoformat() if end_date else None,
        }

        if phonepe_payment:
            redirect_url_phonepe = phonepe_payment.get("redirectUrl") if isinstance(phonepe_payment, dict) else None
            response_payload["phonepe"] = {
                "merchantId": merchant_order_id,
                "merchantTransactionId": transaction_id,
                "amount": amount_paise,
                "currency": policy.get("currency", "INR"),
                "redirectUrl": redirect_url_phonepe,
            }

        return JsonResponse(response_payload)
    except Exception as exc:
        logger.exception("checkout_plan fatal error: %s", exc)
        return _json_error(f"Internal error: {exc}", status=500)


@csrf_exempt
@require_POST
def phonepe_payment_callback(request):
    """Handle PhonePe payment callback/webhook after payment completion."""
    try:
        payload = _parse_body(request)
    except ValueError as error:
        logger.warning("Invalid callback payload: %s", error)
        return JsonResponse({"success": False, "message": "Invalid payload"}, status=400)

    # PhonePe callback structure: typically contains merchantTransactionId and status
    merchant_transaction_id = payload.get("merchantTransactionId") or payload.get("transactionId")
    if not merchant_transaction_id:
        logger.warning("Missing merchantTransactionId in callback")
        return JsonResponse({"success": False, "message": "Missing transaction ID"}, status=400)

    try:
        payment = Payment.objects.get(transaction_id=merchant_transaction_id)
    except Payment.DoesNotExist:
        logger.warning("Payment not found for transaction: %s", merchant_transaction_id)
        return JsonResponse({"success": False, "message": "Payment not found"}, status=404)

    # Update payment status based on PhonePe response
    payment_status = payload.get("code") or payload.get("status", "").upper()
    
    # PhonePe typically returns "PAYMENT_SUCCESS" or "PAYMENT_ERROR"
    if payment_status == "PAYMENT_SUCCESS" or payload.get("success") is True:
        if payment.status != "paid":
            payment.status = "paid"
            payment.save(update_fields=["status", "updated_at"])
            logger.info("Payment marked as paid for transaction: %s", merchant_transaction_id)
    elif payment_status == "PAYMENT_ERROR" or payment_status == "FAILED":
        if payment.status != "failed":
            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])
            logger.info("Payment marked as failed for transaction: %s", merchant_transaction_id)

    # Store PhonePe callback response in metadata
    meta = dict(payment.metadata or {})
    meta["phonepe_callback"] = {
        "payload": payload,
        "received_at": timezone.now().isoformat(),
    }
    payment.metadata = meta
    payment.save(update_fields=["metadata", "updated_at"])

    return JsonResponse({"success": True, "message": "Callback processed"})


def _set_meta_field(meta: dict, key: str, value):
    if value is None:
        return False
    normalized = value.strip() if isinstance(value, str) else value
    if not normalized:
        return False
    if meta.get(key) == normalized:
        return False
    meta[key] = normalized
    return True


@csrf_exempt
@require_POST
def render_basic_certificate(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    transaction_id = (payload.get("transactionId") or "").strip()
    if not transaction_id:
        return _json_error("transactionId is required.")

    try:
        payment = Payment.objects.select_related("course").get(transaction_id=transaction_id)
    except Payment.DoesNotExist:
        return _json_error("Payment not found.", status=404)

    if payment.plan_type != "basic":
        return _json_error("Only basic plan certificates can be rendered with this endpoint.")

    overrides = payload.get("overrides") or {}
    certificate_id_override = overrides.get("certificateId")

    with transaction.atomic():
        dirty_fields = []
        student_name = (overrides.get("studentName") or "").strip()
        if student_name:
            payment.name = student_name
            dirty_fields.append("name")

        metadata = dict(payment.metadata or {})
        certificate_meta = dict(metadata.get("basicCertificate") or {})
        meta_changed = False

        course_override = overrides.get("courseTitle")
        if course_override:
            meta_changed = _set_meta_field(certificate_meta, "courseTitle", course_override) or meta_changed

        award_override = overrides.get("awardDate")
        if award_override:
            parsed_award = _parse_date(award_override)
            if not parsed_award:
                return _json_error("awardDate must be provided in YYYY-MM-DD format.")
            meta_changed = _set_meta_field(certificate_meta, "awardDate", parsed_award.isoformat()) or meta_changed

        qr_override = overrides.get("qrPayload")
        if qr_override:
            meta_changed = _set_meta_field(certificate_meta, "qrPayload", qr_override) or meta_changed

        course_title = certificate_meta.get("courseTitle")
        if not course_title:
            default_course = payment.course.title if payment.course else "Certified Track"
            meta_changed = _set_meta_field(certificate_meta, "courseTitle", default_course) or meta_changed
            course_title = certificate_meta["courseTitle"]

        award_date = certificate_meta.get("awardDate")
        if not award_date:
            award_date = timezone.now().date().isoformat()
            meta_changed = _set_meta_field(certificate_meta, "awardDate", award_date) or meta_changed

        try:
            certificate = _ensure_certificate(payment, certificate_id_override)
        except ValueError as exc:
            return _json_error(str(exc))

        qr_payload = certificate_meta.get("qrPayload")
        if not qr_payload:
            qr_payload = f"{VERIFY_PAGE_URL}?certificateId={certificate.certificate_id}"
            meta_changed = _set_meta_field(certificate_meta, "qrPayload", qr_payload) or meta_changed

        if meta_changed:
            metadata["basicCertificate"] = certificate_meta
            payment.metadata = metadata
            if "metadata" not in dirty_fields:
                dirty_fields.append("metadata")

        if dirty_fields:
            dirty_fields.append("updated_at")
            payment.save(update_fields=dirty_fields)

    plan_meta = PLAN_SIZE_METADATA.get(payment.plan_type, {"size": payment.plan_type, "display": payment.plan_type})

    return JsonResponse(
        {
            "status": "ready",
            "transactionId": payment.transaction_id,
            "planType": payment.plan_type,
            "planSize": plan_meta["size"],
            "planDisplay": plan_meta["display"],
            "certificate": {
                "studentName": payment.name,
                "courseTitle": course_title,
                "certificateId": certificate.certificate_id,
                "awardDate": award_date,
                "qrPayload": qr_payload,
                "orientation": payment.certificate_orientation,
            },
        }
    )


@require_GET
def list_plans(_request):
    data = [_serialize_plan(key, policy) for key, policy in PLAN_RULES.items()]
    return JsonResponse({"plans": data})


@csrf_exempt
@require_POST
def issue_certificate(request):
    """Issue certificate for any plan type and return certificate data."""
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    transaction_id = payload.get("transactionId")
    if not transaction_id:
        return _json_error("transactionId is required.")

    try:
        payment = Payment.objects.select_related("course").get(transaction_id=transaction_id)
    except Payment.DoesNotExist:
        return _json_error("Payment not found.", status=404)

    with transaction.atomic():
        # Ensure payment is marked as paid
        if payment.status != "paid":
            payment.status = "paid"
            payment.save(update_fields=["status", "updated_at"])

        # Issue or get existing certificate
        certificate = _ensure_certificate(payment)

        # Get course title
        course_title = payment.course.title if payment.course else "Certified Track"

        # Generate URLs for verification (QR) and certificate download
        verify_url_raw = f"{VERIFY_PAGE_URL}?certificateId={certificate.certificate_id}"
        download_url_raw = f"{FRONTEND_BASE_URL.rstrip('/')}/certificate/pdf?certificateId={certificate.certificate_id}"

        def _ensure_scheme(url: str) -> str:
            if url.lower().startswith(("http://", "https://")):
                return url
            return f"https://{url.lstrip('/')}"

        verify_url = _ensure_scheme(verify_url_raw)
        download_url = _ensure_scheme(download_url_raw)

        # QR code should point to verification URL
        qr_payload = verify_url

        # Get award date (use start_date if available, otherwise current date)
        award_date = payment.start_date if payment.start_date else timezone.now().date()

    # Resolve plan label (outside transaction block)
    plan_policy = _get_plan_policy(payment.plan_type)
    plan_label = plan_policy.get("label", payment.plan_type.title()) if plan_policy else payment.plan_type.title()

    # Schedule certificate email after a short delay (4 minutes)
    _schedule_certificate_email(
        certificate=certificate,
        payment=payment,
        course_title=course_title,
        plan_label=plan_label,
        verify_url=verify_url,
        download_url=download_url,
        delay_seconds=240,
    )

    return JsonResponse(
        {
            "certificateId": certificate.certificate_id,
            "studentName": payment.name,
            "courseTitle": course_title,
            "projectTitle": (payment.metadata or {}).get("projectTitle") if isinstance(payment.metadata, dict) else None,
            "awardDate": award_date.isoformat(),
            "qrPayload": qr_payload,
            "planType": payment.plan_type,
            "orientation": payment.certificate_orientation,
        }
    )


@csrf_exempt
@require_POST
def fulfillment_handler(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    transaction_id = payload.get("transactionId")
    if not transaction_id:
        return _json_error("transactionId is required.")

    try:
        payment = Payment.objects.select_related("course").get(transaction_id=transaction_id)
    except Payment.DoesNotExist:
        return _json_error("Payment not found.", status=404)

    policy = _get_plan_policy(payment.plan_type)
    if not policy:
        return _json_error("Unsupported plan type.", status=500)

    project_description = payload.get("projectDescription", "").strip()

    if policy["requires_project"] and len(project_description) < 20:
        return _json_error("Project description must be at least 20 characters.")

    with transaction.atomic():
        payment.status = "paid"
        payment.metadata = {
            **payment.metadata,
            "projectDescription": project_description,
        }
        payment.save(update_fields=["status", "metadata", "updated_at"])

        certificate = _issue_certificate(payment, note="Issued via fulfillment handler")

    message = (
        "Project verified. Download unlocked."
        if policy["requires_project"]
        else "Certificate ready for download."
    )
    return JsonResponse(
        {
            "planType": payment.plan_type,
            "downloadAvailable": True,
            "message": message,
            "certificateId": certificate.certificate_id,
        }
    )


@csrf_exempt
@require_POST
def verify_certificate(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    certificate_id = (payload.get("certificateId") or "").strip()
    if not certificate_id:
        return _json_error("certificateId is required.")

    certificate = Certificate.objects.select_related("course", "payment").filter(certificate_id__iexact=certificate_id).first()
    if not certificate:
        return JsonResponse({"certificateId": certificate_id, "verified": False, "message": "Certificate not found."})

    # Get payment details if available
    payment = certificate.payment
    name = payment.name if payment else None
    email = payment.email if payment else certificate.email
    college_name = payment.college_name if payment else None
    transaction_id = payment.transaction_id if payment else None
    awarded_on = certificate.created_at.date().isoformat()
    
    # Calculate time period for industrial/master certificates
    time_period = None
    if certificate.plan_type in ["industrial", "mastery"]:
        if certificate.plan_type == "industrial":
            time_period = "3 months (120 hours)"
        elif certificate.plan_type == "mastery":
            time_period = "6 months (240 hours)"
    
    # Get course duration dates for industrial/master certificates
    awarded_date = certificate.created_at.date()
    end_date = awarded_date.isoformat()
    start_date = (awarded_date - timedelta(days=90)).isoformat()

    return JsonResponse(
        {
            "certificateId": certificate.certificate_id,
            "verified": certificate.status == "issued",
            "holder": {
                "name": name,
                "email": email,
                "planType": certificate.plan_type,
                "course": certificate.course.title if certificate.course else None,
                "awardedOn": awarded_on,
                "college": college_name,
                "transactionId": transaction_id,
                "timePeriod": time_period,
                "startDate": start_date,
                "endDate": end_date,
            },
            "orientation": certificate.orientation,
        }
    )


@csrf_exempt
@require_POST
def recover_certificate(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    email = (payload.get("email") or "").strip()
    if not email:
        return _json_error("Email is required.")

    certificate = (
        Certificate.objects.filter(email__iexact=email, status="issued")
        .order_by("-created_at")
        .first()
    )
    if not certificate:
        return JsonResponse(
            {
                "status": "queued",
                "message": "If a certificate exists for this email, it will be sent shortly.",
                "email": email,
            }
        )

    try:
        send_certificate_email(
            recipient=email,
            subject="Your Fast-Track Certificate",
            body=(
                f"Dear learner,\n\nHere is the reference for certificate {certificate.certificate_id}.\n\n"
                f"For changes or help, call us at +91-9113750231."
            ),
        )
        CertificateDeliveryLog.objects.create(
            certificate=certificate,
            status="sent",
            detail={"trigger": "self-recovery"},
        )
        delivery_status = "dispatched"
        delivery_message = "Certificate emailed to the requested address."
    except GmailSendError as exc:
        delivery_status = "queued"
        delivery_message = f"Email queued: {exc}"
        CertificateDeliveryLog.objects.create(
            certificate=certificate,
            status="failed",
            detail={"trigger": "self-recovery", "reason": str(exc)},
        )

    return JsonResponse(
        {
            "status": delivery_status,
            "message": delivery_message,
            "email": email,
            "certificateId": certificate.certificate_id,
        }
    )


@csrf_exempt
@require_POST
def submit_contact_message(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    subject = (payload.get("subject") or "").strip()
    message = (payload.get("message") or "").strip()
    phone = (payload.get("phone") or "").strip()

    if not name or not email or not subject or not message:
        return _json_error("Name, email, subject, and message are required.")

    ContactMessage.objects.create(
        name=name,
        email=email,
        phone=phone,
        subject=subject,
        message=message,
    )

    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def start_email_otp(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    email = (payload.get("email") or "").strip()
    if not email:
        return _json_error("Email is required.")

    code = f"{random.randint(100000, 999999)}"
    EmailOTP.objects.create(email=email, code=code)

    body = (
        "Your CITS Digital email verification code is "
        f"{code}. This code is valid for 30 minutes. "
        "If you did not request this, you can ignore this email."
    )
    try:
        send_certificate_email(
            recipient=email,
            subject="CITS Digital Email Verification Code",
            body=body,
        )
    except GmailSendError as exc:
        logger.exception("Failed to send OTP email to %s: %s", email, exc)
        return _json_error("Unable to send verification code. Please try again.")

    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def verify_email_otp(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    email = (payload.get("email") or "").strip()
    code = (payload.get("code") or "").strip()
    if not email or not code:
        return _json_error("Email and code are required.")

    cutoff = timezone.now() - timedelta(minutes=30)
    otp = (
        EmailOTP.objects.filter(email__iexact=email, code=code, created_at__gte=cutoff)
        .order_by("-created_at")
        .first()
    )
    if not otp:
        return _json_error("Invalid or expired code.")

    if not otp.verified_at:
        otp.verified_at = timezone.now()
        otp.save(update_fields=["verified_at", "updated_at"])

    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def admin_login(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    password = payload.get("password")
    if password != getattr(settings, "ADMIN_PANEL_PASSWORD", None):
        return _json_error("Invalid credentials.", status=401)

    signer = signing.TimestampSigner(settings.SECRET_KEY)
    token = signer.sign("admin")
    return JsonResponse(
        {
            "token": token,
            "expiresIn": ADMIN_TOKEN_TTL_SECONDS,
        }
    )


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def admin_payments(request):
    auth_error = _validate_admin_request(request)
    if auth_error:
        return auth_error

    if request.method == "GET":
        payments = Payment.objects.select_related("course").order_by("-created_at")[:200]
        return JsonResponse(
            {
                "payments": [
                    {
                        "transactionId": payment.transaction_id,
                        "planType": payment.plan_type,
                        "email": payment.email,
                        "name": payment.name,
                        "phone": payment.phone,
                        "course": payment.course.title if payment.course else None,
                        "status": payment.status,
                        "amount": float(payment.amount),
                        "orientation": payment.certificate_orientation,
                        "startDate": payment.start_date.isoformat() if payment.start_date else None,
                        "endDate": payment.end_date.isoformat() if payment.end_date else None,
                    }
                    for payment in payments
                ]
            }
        )

    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    transaction_id = payload.get("transactionId")
    if not transaction_id:
        return _json_error("transactionId is required.")

    try:
        payment = Payment.objects.get(transaction_id=transaction_id)
    except Payment.DoesNotExist:
        return _json_error("Payment not found.", status=404)

    editable_fields = {
        "email": "email",
        "phone": "phone",
        "collegeName": "college_name",
        "semester": "semester",
        "certificateOrientation": "certificate_orientation",
    }
    dirty_fields = []
    for payload_key, model_field in editable_fields.items():
        if payload_key in payload:
            setattr(payment, model_field, payload[payload_key])
            dirty_fields.append(model_field)
    if dirty_fields:
        dirty_fields.append("updated_at")
        payment.save(update_fields=dirty_fields)

    return JsonResponse({"status": "updated"})


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def admin_certificates(request):
    auth_error = _validate_admin_request(request)
    if auth_error:
        return auth_error

    if request.method == "GET":
        certificates = Certificate.objects.select_related("course", "payment").order_by("-created_at")[:200]
        return JsonResponse(
            {
                "certificates": [
                    {
                        "certificateId": cert.certificate_id,
                        "email": cert.email,
                        "planType": cert.plan_type,
                        "course": cert.course.title if cert.course else None,
                        "status": cert.status,
                        "orientation": cert.orientation,
                        "transactionId": cert.payment.transaction_id if cert.payment else None,
                    }
                    for cert in certificates
                ]
            }
        )

    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    certificate_id = payload.get("certificateId")
    if not certificate_id:
        return _json_error("certificateId is required.")

    certificate = Certificate.objects.filter(certificate_id=certificate_id).first()
    if not certificate:
        return _json_error("Certificate not found.", status=404)

    dirty_fields = []
    if "email" in payload:
        certificate.email = payload["email"]
        dirty_fields.append("email")
    if "status" in payload:
        certificate.status = payload["status"]
        dirty_fields.append("status")
    if dirty_fields:
        dirty_fields.append("updated_at")
        certificate.save(update_fields=dirty_fields)
    return JsonResponse({"status": "updated"})


@csrf_exempt
@require_POST
def admin_send_certificate(request, certificate_id):
    auth_error = _validate_admin_request(request)
    if auth_error:
        return auth_error

    certificate = Certificate.objects.select_related("course").filter(certificate_id=certificate_id).first()
    if not certificate:
        return _json_error("Certificate not found.", status=404)

    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    recipient = payload.get("email") or certificate.email
    if not recipient:
        return _json_error("Recipient email is required.")

    try:
        send_certificate_email(
            recipient=recipient,
            subject=f"Certificate {certificate.certificate_id}",
            body=(
                f"Hi,\n\nPlease find the confirmation for certificate {certificate.certificate_id} ({certificate.plan_type}).\n\n"
                f"If you need any changes or help, call us at +91-9113750231."
            ),
        )
        CertificateDeliveryLog.objects.create(
            certificate=certificate,
            status="sent",
            detail={"trigger": "admin-panel", "recipient": recipient},
        )
        return JsonResponse({"status": "sent", "recipient": recipient})
    except GmailSendError as exc:
        CertificateDeliveryLog.objects.create(
            certificate=certificate,
            status="failed",
            detail={"trigger": "admin-panel", "recipient": recipient, "reason": str(exc)},
        )
        return _json_error(str(exc), status=502)


@csrf_exempt
@require_POST
def submit_contact_message(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    subject = (payload.get("subject") or "").strip()
    message = (payload.get("message") or "").strip()
    phone = (payload.get("phone") or "").strip()

    if not name or not email or not subject or not message:
        return _json_error("Name, email, subject, and message are required.")

    ContactMessage.objects.create(
        name=name,
        email=email,
        phone=phone,
        subject=subject,
        message=message,
    )

    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def start_email_otp(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    email = (payload.get("email") or "").strip()
    if not email:
        return _json_error("Email is required.")

    code = f"{random.randint(100000, 999999)}"
    EmailOTP.objects.create(email=email, code=code)

    body = (
        "Your CITS Digital email verification code is "
        f"{code}. This code is valid for 30 minutes. "
        "If you did not request this, you can ignore this email."
    )
    try:
        send_certificate_email(
            recipient=email,
            subject="CITS Digital Email Verification Code",
            body=body,
        )
    except GmailSendError as exc:
        logger.exception("Failed to send OTP email to %s: %s", email, exc)
        return _json_error("Unable to send verification code. Please try again.")

    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def verify_email_otp(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    email = (payload.get("email") or "").strip()
    code = (payload.get("code") or "").strip()
    if not email or not code:
        return _json_error("Email and code are required.")

    cutoff = timezone.now() - timedelta(minutes=30)
    otp = (
        EmailOTP.objects.filter(email__iexact=email, code=code, created_at__gte=cutoff)
        .order_by("-created_at")
        .first()
    )
    if not otp:
        return _json_error("Invalid or expired code.")

    if not otp.verified_at:
        otp.verified_at = timezone.now()
        otp.save(update_fields=["verified_at", "updated_at"])

    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def admin_login(request):
    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    password = payload.get("password")
    if password != getattr(settings, "ADMIN_PANEL_PASSWORD", None):
        return _json_error("Invalid credentials.", status=401)

    signer = signing.TimestampSigner(settings.SECRET_KEY)
    token = signer.sign("admin")
    return JsonResponse(
        {
            "token": token,
            "expiresIn": ADMIN_TOKEN_TTL_SECONDS,
        }
    )


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def admin_payments(request):
    auth_error = _validate_admin_request(request)
    if auth_error:
        return auth_error

    if request.method == "GET":
        payments = Payment.objects.select_related("course").order_by("-created_at")[:200]
        return JsonResponse(
            {
                "payments": [
                    {
                        "transactionId": payment.transaction_id,
                        "planType": payment.plan_type,
                        "email": payment.email,
                        "name": payment.name,
                        "phone": payment.phone,
                        "course": payment.course.title if payment.course else None,
                        "status": payment.status,
                        "amount": float(payment.amount),
                        "orientation": payment.certificate_orientation,
                        "startDate": payment.start_date.isoformat() if payment.start_date else None,
                        "endDate": payment.end_date.isoformat() if payment.end_date else None,
                    }
                    for payment in payments
                ]
            }
        )

    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    transaction_id = payload.get("transactionId")
    if not transaction_id:
        return _json_error("transactionId is required.")

    try:
        payment = Payment.objects.get(transaction_id=transaction_id)
    except Payment.DoesNotExist:
        return _json_error("Payment not found.", status=404)

    editable_fields = {
        "email": "email",
        "phone": "phone",
        "collegeName": "college_name",
        "semester": "semester",
        "certificateOrientation": "certificate_orientation",
    }
    dirty_fields = []
    for payload_key, model_field in editable_fields.items():
        if payload_key in payload:
            setattr(payment, model_field, payload[payload_key])
            dirty_fields.append(model_field)
    if dirty_fields:
        dirty_fields.append("updated_at")
        payment.save(update_fields=dirty_fields)

    return JsonResponse({"status": "updated"})


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def admin_certificates(request):
    auth_error = _validate_admin_request(request)
    if auth_error:
        return auth_error

    if request.method == "GET":
        certificates = Certificate.objects.select_related("course", "payment").order_by("-created_at")[:200]
        return JsonResponse(
            {
                "certificates": [
                    {
                        "certificateId": cert.certificate_id,
                        "email": cert.email,
                        "planType": cert.plan_type,
                        "course": cert.course.title if cert.course else None,
                        "status": cert.status,
                        "orientation": cert.orientation,
                        "transactionId": cert.payment.transaction_id if cert.payment else None,
                    }
                    for cert in certificates
                ]
            }
        )

    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    certificate_id = payload.get("certificateId")
    if not certificate_id:
        return _json_error("certificateId is required.")

    certificate = Certificate.objects.filter(certificate_id=certificate_id).first()
    if not certificate:
        return _json_error("Certificate not found.", status=404)

    dirty_fields = []
    if "email" in payload:
        certificate.email = payload["email"]
        dirty_fields.append("email")
    if "status" in payload:
        certificate.status = payload["status"]
        dirty_fields.append("status")
    if dirty_fields:
        dirty_fields.append("updated_at")
        certificate.save(update_fields=dirty_fields)
    return JsonResponse({"status": "updated"})


@csrf_exempt
@require_POST
def admin_send_certificate(request, certificate_id):
    auth_error = _validate_admin_request(request)
    if auth_error:
        return auth_error

    certificate = Certificate.objects.select_related("course").filter(certificate_id=certificate_id).first()
    if not certificate:
        return _json_error("Certificate not found.", status=404)

    try:
        payload = _parse_body(request)
    except ValueError as error:
        return _json_error(str(error))

    recipient = payload.get("email") or certificate.email
    if not recipient:
        return _json_error("Recipient email is required.")

    try:
        send_certificate_email(
            recipient=recipient,
            subject=f"Certificate {certificate.certificate_id}",
            body=f"Hi,\n\nPlease find the confirmation for certificate {certificate.certificate_id} ({certificate.plan_type}).",
        )
        CertificateDeliveryLog.objects.create(
            certificate=certificate,
            status="sent",
            detail={"trigger": "admin-panel", "recipient": recipient},
        )
        return JsonResponse({"status": "sent", "recipient": recipient})
    except GmailSendError as exc:
        CertificateDeliveryLog.objects.create(
            certificate=certificate,
            status="failed",
            detail={"trigger": "admin-panel", "recipient": recipient, "reason": str(exc)},
        )
        return _json_error(str(exc), status=502)
