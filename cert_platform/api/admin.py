from django.contrib import admin

from .models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    Certificate,
    CertificateDeliveryLog,
    ContactMessage,
    Course,
    EmailOTP,
    Payment,
)


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "subject", "updated_at")
    search_fields = ("title", "slug", "subject")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "duration_minutes", "pass_threshold", "is_active")
    list_filter = ("course", "is_active")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [AssessmentQuestionInline]


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = ("assessment", "email", "score_percent", "passed", "created_at")
    list_filter = ("passed", "assessment")
    search_fields = ("email",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "plan_type", "email", "amount", "status", "created_at")
    list_filter = ("plan_type", "status", "created_at", "certificate_orientation")
    search_fields = ("transaction_id", "email", "name")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_id", "email", "plan_type", "status", "created_at")
    list_filter = ("plan_type", "status", "orientation")
    search_fields = ("certificate_id", "email")


@admin.register(CertificateDeliveryLog)
class CertificateDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ("certificate", "channel", "status", "created_at")
    list_filter = ("channel", "status")
    search_fields = ("certificate__certificate_id",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at")
    search_fields = ("name", "email", "subject", "message")
    list_filter = ("created_at",)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "code", "created_at", "verified_at")
    search_fields = ("email",)
    list_filter = ("created_at",)

    search_fields = ("certificate__certificate_id",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at")
    search_fields = ("name", "email", "subject", "message")
    list_filter = ("created_at",)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "code", "created_at", "verified_at")
    search_fields = ("email",)
    list_filter = ("created_at",)
