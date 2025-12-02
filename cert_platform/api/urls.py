from django.urls import path

from . import views


urlpatterns = [
    path("health/", views.health_check, name="health-check"),
    path("syllabus/", views.get_syllabus, name="syllabus"),
    path("courses/", views.list_courses, name="courses"),
    path("assessments/", views.list_assessments, name="assessments"),
    path("assessment/questions/", views.list_questions, name="assessment-questions"),
    path("assessment/submit/", views.submit_assessment, name="assessment-submit"),
    path("plans/", views.list_plans, name="plans"),
    path("payment/checkout/", views.checkout_plan, name="checkout"),
    path("certificate/basic/render/", views.render_basic_certificate, name="basic-certificate-render"),
    path("certificate/issue/", views.issue_certificate, name="issue-certificate"),
    path("fulfillment/progress/", views.fulfillment_handler, name="fulfillment"),
    path("verify/", views.verify_certificate, name="verify"),
    path("recover/", views.recover_certificate, name="recover"),
    path("contact/", views.submit_contact_message, name="contact"),
    path("auth/email/otp/start/", views.start_email_otp, name="email-otp-start"),
    path("auth/email/otp/verify/", views.verify_email_otp, name="email-otp-verify"),
    path("admin/login/", views.admin_login, name="admin-login"),
    path("admin/payments/", views.admin_payments, name="admin-payments"),
    path("admin/certificates/", views.admin_certificates, name="admin-certificates"),
    path("admin/certificates/<str:certificate_id>/send/", views.admin_send_certificate, name="admin-certificates-send"),
]


]

