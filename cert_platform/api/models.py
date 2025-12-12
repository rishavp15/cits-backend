from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Course(TimeStampedModel):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=150)
    description = models.TextField()
    # SEO metadata (optional per-course)
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    seo_keywords = models.CharField(max_length=320, blank=True)
    og_image_url = models.URLField(blank=True)
    hero_tagline = models.CharField(max_length=200)
    hero_title = models.CharField(max_length=200)
    hero_description = models.TextField()
    hero_image_url = models.URLField(blank=True)
    card_image_url = models.URLField(blank=True)
    gallery_images = models.JSONField(default=list, blank=True)
    trust_grid = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    testimonials = models.JSONField(default=list, blank=True)  # Deprecated - use Testimonial model instead
    subject = models.CharField(max_length=150, blank=True)
    icon = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=40, blank=True)
    students = models.PositiveIntegerField(default=0)
    duration_hours = models.PositiveIntegerField(default=0)
    logo_url = models.URLField(blank=True)
    syllabus = models.JSONField(default=list, blank=True)
    class_links = models.JSONField(default=list, blank=True)
    competencies = models.JSONField(default=list, blank=True)
    plan_highlights = models.JSONField(default=dict, blank=True)
    certificate_types = models.JSONField(default=list, blank=True)
    open_standards_label = models.CharField(max_length=200, blank=True)
    playlist_modules = models.JSONField(default=list, blank=True)
    project_title_suggestions = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.title


class Testimonial(TimeStampedModel):
    """Testimonial model with SEO fields for better search engine visibility"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="testimonial_entries")
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=150, blank=True)
    quote = models.TextField()
    image = models.URLField(blank=True, help_text="URL to the testimonial author's image/avatar")
    # SEO fields for this testimonial
    seo_title = models.CharField(max_length=180, blank=True, help_text="SEO title for this testimonial (e.g., 'Student Review: [Name] - [Course]')")
    seo_description = models.CharField(max_length=320, blank=True, help_text="SEO description/meta description for this testimonial")
    seo_keywords = models.CharField(max_length=320, blank=True, help_text="Comma-separated keywords for SEO")
    og_image_url = models.URLField(blank=True, help_text="Open Graph image URL for social media sharing")
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower numbers appear first)")
    is_active = models.BooleanField(default=True, help_text="Show this testimonial on the course page")

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"

    def __str__(self):
        return f"{self.name} - {self.course.title if self.course else 'No Course'}"


class Assessment(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assessments")
    title = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    duration_minutes = models.PositiveIntegerField(default=15)
    pass_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=40.0)
    instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class AssessmentQuestion(TimeStampedModel):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    options = models.JSONField(default=list)
    answer = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.assessment.slug} Q{self.order}"


class AssessmentAttempt(TimeStampedModel):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="attempts")
    email = models.EmailField(blank=True)
    score_percent = models.DecimalField(max_digits=5, decimal_places=2)
    passed = models.BooleanField(default=False)
    responses = models.JSONField(default=list)
    correct_count = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]


class Payment(TimeStampedModel):
    PLAN_CHOICES = [
        ("basic", "Basic"),
        ("industrial", "Industrial Training"),
        ("mastery", "Mastery Certification"),
    ]

    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    ORIENTATION_CHOICES = [
        ("horizontal", "Horizontal"),
        ("vertical", "Vertical"),
    ]

    transaction_id = models.CharField(max_length=40, unique=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    assessment = models.ForeignKey(Assessment, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    college_name = models.CharField(max_length=150, blank=True)
    semester = models.CharField(max_length=40, blank=True)
    project_link = models.URLField(blank=True)
    repository_link = models.URLField(blank=True)
    certificate_orientation = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, default="horizontal")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initiated")
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.transaction_id} ({self.status})"


class PlanConfig(TimeStampedModel):
    PLAN_CHOICES = [
        ("basic", "Basic"),
        ("industrial", "Industrial Training"),
        ("mastery", "Mastery Certification"),
    ]

    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="INR")
    label_override = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Plan Configuration"
        verbose_name_plural = "Plan Configurations"

    @property
    def discount_percent(self):
        """Calculate discount percentage from original_price and price"""
        if self.original_price and self.original_price > self.price:
            return round(100 - (float(self.price) / float(self.original_price) * 100), 2)
        return 0

    def __str__(self):
        return f"{self.get_plan_type_display()} - {self.price} {self.currency}"


class Certificate(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("issued", "Issued"),
        ("revoked", "Revoked"),
    ]

    certificate_id = models.CharField(max_length=40, unique=True)
    email = models.EmailField()
    plan_type = models.CharField(max_length=20, choices=Payment.PLAN_CHOICES)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="certificates")
    orientation = models.CharField(max_length=20, choices=Payment.ORIENTATION_CHOICES, default="horizontal")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    download_url = models.URLField(blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="certificates")

    def __str__(self):
        return self.certificate_id


class CertificateDeliveryLog(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name="delivery_logs")
    channel = models.CharField(max_length=40, default="email")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    detail = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.certificate.certificate_id} via {self.channel}"


class ContactMessage(TimeStampedModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.subject}"


class EmailOTP(TimeStampedModel):
    email = models.EmailField()
    code = models.CharField(max_length=10)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.email}"

