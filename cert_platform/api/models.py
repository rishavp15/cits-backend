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
    hero_tagline = models.CharField(max_length=200)
    hero_title = models.CharField(max_length=200)
    hero_description = models.TextField()
    hero_image_url = models.URLField(blank=True)
    card_image_url = models.URLField(blank=True)
    gallery_images = models.JSONField(default=list, blank=True)
    trust_grid = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    testimonials = models.JSONField(default=list, blank=True)
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

    def __str__(self):
        return self.title


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

