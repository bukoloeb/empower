import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Count

# App specific imports
from .models import User
from .forms import UserUpdateForm
from .utils import generate_and_send_pin
from courses.models import Course, Enrollment, LessonCompletion


# --- AUTHENTICATION FLOW ---

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone = request.POST.get('phone_number')
        address = request.POST.get('address')
        role = request.POST.get('role', User.Role.LEARNER)

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'users/register.html')

        # Create user but keep them unverified
        user = User.objects.create_user(
            email=email,
            password=password,
            phone_number=phone,
            address=address,
            role=role,
            is_active=False  # Prevent login until PIN is verified
        )

        generate_and_send_pin(user)

        # Store email in session to use on the verification page
        request.session['verification_email'] = email
        return redirect('verify_pin')

    return render(request, 'users/register.html')


def verify_pin_view(request):
    email = request.session.get('verification_email')
    if not email:
        return redirect('login')

    if request.method == 'POST':
        entered_pin = request.POST.get('pin')
        try:
            user = User.objects.get(email=email, verification_pin=entered_pin)

            # Activate and verify the user
            user.is_active = True
            user.is_verified = True
            user.verification_pin = None  # Clear pin after use
            user.save()

            # Log the user in immediately for a better experience
            login(request, user)

            messages.success(request, f"Welcome, {user.email}! Your account is verified.")
            return redirect('home')
        except User.DoesNotExist:
            messages.error(request, "Invalid PIN. Please try again.")

    return render(request, 'users/verify_pin.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.is_active:
                # Multi-factor style PIN login
                generate_and_send_pin(user)
                request.session['verification_email'] = email
                messages.info(request, "A login PIN has been sent to your email.")
                return redirect('verify_pin')
            else:
                messages.error(request, "This account is disabled.")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, 'users/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')


# --- USER SETTINGS & TRAFFIC CONTROL ---

@login_required
def profile_settings(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile_settings')
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, 'users/settings.html', {'form': form})


@login_required
def home_view(request):
    """Traffic controller to specific dashboards based on role."""
    if request.user.role == User.Role.EDUCATOR:
        return redirect('educator_dashboard')
    return redirect('learner_dashboard')


# --- DASHBOARDS ---

@login_required
def educator_dashboard(request):
    """Dashboard for Instructors to manage their created courses."""
    if request.user.role != User.Role.EDUCATOR:
        messages.error(request, "Access denied. Educator account required.")
        return redirect('learner_dashboard')

    # Fetch courses created by this user
    my_courses = Course.objects.filter(educator=request.user).annotate(
        student_count=Count('enrollments')
    ).order_by('-created_at')

    return render(request, 'users/educator_dashboard.html', {'my_courses': my_courses})


@login_required
def learner_dashboard(request):
    """Personalized dashboard for students showing their progress."""
    enrollments = Enrollment.objects.filter(student=request.user).select_related('course')
    enrolled_courses_progress = []

    for enrollment in enrollments:
        course = enrollment.course
        # Correctly aggregate lessons across all modules in the course
        total_lessons = LessonCompletion.objects.filter(lesson__module__course=course).count()

        # This count should ideally come from a direct query on Lesson model for accuracy
        from courses.models import Lesson
        total_lessons_count = Lesson.objects.filter(module__course=course).count()

        completed_lessons = LessonCompletion.objects.filter(
            student=request.user,
            lesson__module__course=course
        ).count()

        progress_percent = int((completed_lessons / total_lessons_count) * 100) if total_lessons_count > 0 else 0

        enrolled_courses_progress.append({
            'course': course,
            'progress': progress_percent,
        })

    return render(request, 'users/learner_dashboard.html', {'enrolled_courses': enrolled_courses_progress})