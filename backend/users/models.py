from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    # 1. Define the Choices
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        EDUCATOR = "EDUCATOR", "Educator"
        LEARNER = "LEARNER", "Learner"

    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    # 2. Add the Role Field
    role = models.CharField(
        max_length=10, 
        choices=Role.choices, 
        default=Role.LEARNER
    )
    
    verification_pin = models.CharField(max_length=6, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"

class Institution(models.Model):
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class LearnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learner_profile')
    interests = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"Learner: {self.user.email}"

class EducatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='educator_profile')
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True)
    bio = models.TextField(blank=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Educator: {self.user.email}"