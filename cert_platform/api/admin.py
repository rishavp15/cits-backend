from django.contrib import admin
from django import forms
from django.forms import Textarea

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
    PlanConfig,
)


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 1


class CourseAdminForm(forms.ModelForm):
    playlist_modules = forms.JSONField(
        required=False,
        help_text='''Format: Array of modules, each with:
- title: Module title
- description: Module description  
- videos: Array of video objects with:
  - url: YouTube URL
  - title: Video title
  - duration: Duration (e.g., "45m")
Example: [{"title": "Python Basics", "description": "Learn Python", "videos": [{"url": "https://youtube.com/watch?v=...", "title": "Intro", "duration": "30m"}]}]''',
        widget=Textarea(
            attrs={
                "rows": 25,
                "style": "font-family: 'Courier New', monospace; font-size: 13px; width: 100%;",
            }
        ),
    )

    class Meta:
        model = Course
        fields = "__all__"
        widgets = {
            "gallery_images": Textarea(attrs={"rows": 5, "style": "font-family: monospace;"}),
            "trust_grid": Textarea(attrs={"rows": 5, "style": "font-family: monospace;"}),
        }


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ("title", "slug", "subject", "updated_at")
    search_fields = ("title", "slug", "subject")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Basic Information", {
            "fields": ("title", "slug", "subject", "description"),
        }),
        ("SEO Settings", {
            "fields": ("seo_title", "seo_description", "seo_keywords", "og_image_url"),
            "classes": ("collapse",),
        }),
        ("Hero Section", {
            "fields": ("hero_tagline", "hero_title", "hero_description", "hero_image_url", "card_image_url"),
        }),
        ("Media & Trust", {
            "fields": ("gallery_images", "trust_grid"),
            "classes": ("collapse",),
        }),
        ("Playlist Modules (Main Content)", {
            "fields": ("playlist_modules",),
            "description": "Add playlist modules with videos. Each module should have: title, description, and videos array with url, title, and duration.",
        }),
    )


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


@admin.register(PlanConfig)
class PlanConfigAdmin(admin.ModelAdmin):
    list_display = ("plan_type", "price", "original_price", "discount_display", "currency", "is_active", "updated_at")
    list_filter = ("plan_type", "is_active")
    search_fields = ("plan_type",)
    fields = ("plan_type", "price", "original_price", "currency", "label_override", "is_active")
    readonly_fields = ("discount_display",)
    
    def discount_display(self, obj):
        """Display discount percentage"""
        discount = obj.discount_percent
        if discount > 0:
            return f"{discount}% OFF"
        return "No discount"
    discount_display.short_description = "Discount"
