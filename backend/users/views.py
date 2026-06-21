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

# Course app models import
from courses.models import Course, Enrollment, Lesson, LessonCompletion


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

        user = User.objects.create_user(
            email=email,
            password=password,
            phone_number=phone,
            address=address,
            role=role,
            is_active=False
        )

        generate_and_send_pin(user)
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
            user.is_active = True
            user.is_verified = True
            user.verification_pin = None
            user.save()
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
    if request.user.role == User.Role.EDUCATOR:
        return redirect('educator_dashboard')
    return redirect('learner_dashboard')


# --- DASHBOARDS ---

@login_required
def educator_dashboard_view(request):
    """Analytics-driven workspace for instructors to inspect student engagement and previews."""
    courses = Course.objects.filter(educator=request.user).select_related('category')

    total_students_enrolled = 0
    total_courses_completed = 0
    total_lessons_finished = 0

    max_enrollment = -1
    most_enrolled_course_title = "None yet"

    my_courses_data = []

    for course in courses:
        student_count = Enrollment.objects.filter(course=course).count()
        completed_count = Enrollment.objects.filter(course=course, is_completed=True).count()

        lessons_in_course = Lesson.objects.filter(module__course=course)
        total_lessons_count = lessons_in_course.count()

        lesson_completions_count = LessonCompletion.objects.filter(
            lesson__module__course=course
        ).count()

        preview_lessons_count = lessons_in_course.filter(is_preview=True).count()

        # Dynamically identify the single most popular course path
        if student_count > max_enrollment and student_count > 0:
            max_enrollment = student_count
            most_enrolled_course_title = course.title

        total_students_enrolled += student_count
        total_courses_completed += completed_count
        total_lessons_finished += lesson_completions_count

        my_courses_data.append({
            'course': course,
            'slug': course.slug,
            'title': course.title,
            'thumbnail': course.thumbnail if course.thumbnail else None,
            'level': course.get_level_display(),
            'is_published': course.is_published,
            'student_count': student_count,
            'completed_count': completed_count,
            'total_lessons_count': total_lessons_count,
            'lesson_completions_count': lesson_completions_count,
            'preview_lessons_count': preview_lessons_count,
        })

    total_expected_lessons = sum(c['student_count'] * c['total_lessons_count'] for c in my_courses_data)
    engagement_rate = int((total_lessons_finished / total_expected_lessons) * 100) if total_expected_lessons > 0 else 0

    context = {
        'my_courses': my_courses_data,
        'total_students_enrolled': total_students_enrolled,
        'total_courses_completed': total_courses_completed,
        'engagement_rate': engagement_rate,
        'total_lessons_finished': total_lessons_finished,
        'most_enrolled_course': most_enrolled_course_title, # Sent to frontend
    }
    return render(request, 'users/educator_dashboard.html', context)


@login_required
def learner_dashboard(request):
    enrollments = Enrollment.objects.filter(student=request.user).select_related('course')
    enrolled_courses_progress = []

    for enrollment in enrollments:
        course = enrollment.course
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