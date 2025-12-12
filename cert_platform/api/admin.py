from django.contrib import admin
from django import forms
from django.forms import Textarea
import json

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
    Testimonial,
)


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 1


class TestimonialInline(admin.StackedInline):
    model = Testimonial
    extra = 1
    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "role", "quote", "image", "order", "is_active"),
        }),
        ("SEO Settings", {
            "fields": ("seo_title", "seo_description", "seo_keywords", "og_image_url"),
            "classes": ("collapse",),
            "description": "SEO fields for this testimonial to improve search engine visibility and social media sharing.",
        }),
    )
    verbose_name = "Testimonial"
    verbose_name_plural = "Testimonials"


class ProjectTitleSuggestionsField(forms.Field):
    """Custom field for project title suggestions - converts between newline-separated text and JSON array"""
    
    widget = Textarea(attrs={
        "rows": 10,
        "style": "width: 100%; font-family: Arial, sans-serif;",
        "placeholder": "Enter one project title per line\nExample:\nE-Commerce Website\nTask Management System\nBlog Platform"
    })
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('help_text', 'Enter one project title per line. Users will see these as suggestions in a dropdown when filling the payment form.')
        super().__init__(*args, **kwargs)
    
    def prepare_value(self, value):
        """Convert JSON array to newline-separated text for display"""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        if isinstance(value, list):
            return "\n".join(str(item).strip() for item in value if item)
        return ""
    
    def to_python(self, value):
        """Convert newline-separated text to list"""
        if not value:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if item]
        # Split by newlines and filter empty lines
        lines = [line.strip() for line in str(value).split("\n") if line.strip()]
        return lines
    
    def clean(self, value):
        """Return as list (will be converted to JSON by the model)"""
        return self.to_python(value)


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
    
    project_title_suggestions = ProjectTitleSuggestionsField()

    class Meta:
        model = Course
        fields = "__all__"
        widgets = {
            "gallery_images": Textarea(attrs={"rows": 5, "style": "font-family: monospace;"}),
            "trust_grid": Textarea(attrs={"rows": 5, "style": "font-family: monospace;"}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # The custom field already returns a list, JSONField will handle serialization
        if commit:
            instance.save()
        return instance


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ("title", "slug", "subject", "students", "duration_hours", "updated_at")
    search_fields = ("title", "slug", "subject")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [TestimonialInline]
    list_filter = ("subject", "updated_at")
    fieldsets = (
        ("Basic Information", {
            "fields": ("title", "slug", "subject", "description"),
        }),
        ("Course Statistics", {
            "fields": ("students", "duration_hours"),
            "description": "Manage the number of enrolled students and course duration displayed on the course page.",
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
        ("Project Title Suggestions", {
            "fields": ("project_title_suggestions",),
            "description": "Add suggested project titles for this course. Users will see these as dropdown options when filling the payment form. Enter one project title per line.",
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


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "role", "order", "is_active", "created_at")
    list_filter = ("course", "is_active", "created_at")
    search_fields = ("name", "role", "quote", "course__title")
    fieldsets = (
        ("Basic Information", {
            "fields": ("course", "name", "role", "quote", "image", "order", "is_active"),
        }),
        ("SEO Settings", {
            "fields": ("seo_title", "seo_description", "seo_keywords", "og_image_url"),
            "description": "SEO fields for this testimonial to improve search engine visibility and social media sharing.",
            "classes": ("collapse",),
        }),
    )
    ordering = ("course", "order", "created_at")
