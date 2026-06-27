from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome or Heroicon name")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Course(models.Model):
    LEVEL_CHOICES = (
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='BEGINNER')
    
    # Metadata & Professional Features
    skills_gained = models.CharField(max_length=500, help_text="e.g. Python, Data Analysis, SQL")
    educator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_created')
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    estimated_duration = models.DurationField(null=True, blank=True, help_text="Format: HH:MM:SS")
    
    # Certification Logic
    provides_certificate = models.BooleanField(default=True)
    passing_percentage = models.PositiveIntegerField(default=70)

    # Status & Tracking
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    certificate_logo = models.ImageField(
        upload_to='certificate_logos/',
        blank=True,
        null=True,
        help_text="Upload brand/company logo for the certificate footer"
    )
    primary_signatory_name = models.CharField(
        max_length=100,
        default="Charles Bukolo",
        help_text="Name of the course creator/primary authority"
    )
    primary_signatory_title = models.CharField(
        max_length=100,
        default="Empower Edge",
        help_text="Title/Organization of the primary signatory"
    )
    primary_signature_image = models.ImageField(
        upload_to='certificate_signatures/',
        blank=True,
        null=True,
        help_text="Upload signature image line overlay"
    )

    secondary_signatory_name = models.CharField(
        max_length=100,
        default="Chitongwa Banda",
        help_text="Collaborator name (e.g., BeRelevant Afrika)"
    )
    secondary_signatory_title = models.CharField(
        max_length=100,
        default="BeRelevant Afrika",
        help_text="Title/Organization of the secondary signatory"
    )
    secondary_signature_image = models.ImageField(
        upload_to='certificate_signatures/',
        blank=True,
        null=True,
        help_text="Upload partner authority signature overlay"
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Module(models.Model):
    course = models.ForeignKey(Course, related_name='modules', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    """Handles the actual delivery of content (Video, Audio, Text, PDF)"""
    CONTENT_TYPES = (
        ('VIDEO', 'Video'),
        ('AUDIO', 'Audio'),
        ('PDF', 'Document/PDF'),
        ('TEXT', 'Text/Article'),
    )
    
    module = models.ForeignKey(Module, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    # backend/courses/models.py
    video_file = models.FileField(upload_to='course_videos/', blank=True, null=True)
    # Content Fields
    video_url = models.URLField(blank=True, null=True, help_text="Link to YouTube, Vimeo, or S3")
    audio_file = models.FileField(upload_to='course_audio/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='course_pdfs/', blank=True, null=True)
    text_content = models.TextField(blank=True, null=True)
    
    order = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False, help_text="Can students see this before buying?")

    class Meta:
        ordering = ['order']

    def get_embed_url(self):
        if "watch?v=" in self.video_url:
            return self.video_url.replace("watch?v=", "embed/")
        return self.video_url

    def __str__(self):
        return f"{self.module.title} - {self.title}"


class LessonCompletion(models.Model):
    """Tracks which lessons a student has finished"""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'lesson'] # A student can't complete the same lesson twice

    def __str__(self):
        return f"{self.student.username} completed {self.lesson.title}"
class Quiz(models.Model):
    # If module is null, it's considered a Final Course Exam
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_quizzes')
    title = models.CharField(max_length=255)
    is_final_exam = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.text[:50]

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class QuizSubmission(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='submissions')
    score = models.PositiveIntegerField()
    passed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.email} - {self.quiz.title} - {self.score}%"
class Resource(models.Model):
    """Extra downloadable materials for the whole course"""
    course = models.ForeignKey(Course, related_name='resources', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='course_resources/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'course') # Prevent double enrollment

    def __str__(self):
        return f"{self.student.email} enrolled in {self.course.title}"
    


def course_player_view(request, slug):
    course = get_object_or_404(Course, slug=slug)
    
    # Check if the user is enrolled
    if not Enrollment.objects.filter(student=request.user, course=course).exists():
        return redirect('course_detail', slug=slug)
    
    # Get the current lesson (default to the first lesson of the first module)
    lesson_id = request.GET.get('lesson')
    if lesson_id:
        current_lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    else:
        # Get the very first lesson of the course
        first_module = course.modules.first()
        current_lesson = first_module.lessons.first() if first_module else None

    context = {
        'course': course,
        'current_lesson': current_lesson,
    }
    return render(request, 'courses/course_player.html', context)