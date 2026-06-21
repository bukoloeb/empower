import io
import json
import os
import mimetypes
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, FileResponse, HttpResponse
from django.db.models import Count
from django.utils import timezone
from django.contrib import messages

# ReportLab Imports for Certificates
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.lib.colors import blue, HexColor

# Models and Forms
from .models import (
    Course, Lesson, Module, Enrollment,
    LessonCompletion, Category, Quiz,
    Question, Choice, QuizSubmission
)
from .forms import CourseForm, LessonForm

# Helper Logic for Video Streaming
from ranged_response import RangedFileResponse


# --- HELPER UTILITIES ---

def stream_video(request, video_path):
    """Helper to handle byte-range requests for smooth video seeking."""
    content_type, _ = mimetypes.guess_type(video_path)
    content_type = content_type or 'video/mp4'
    response = RangedFileResponse(request, open(video_path, 'rb'), content_type=content_type)
    response['Accept-Ranges'] = 'bytes'
    return response


@login_required
def lesson_video_stream(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if not lesson.video_file:
        return HttpResponse(status=404)

    video_path = lesson.video_file.path
    if not os.path.exists(video_path):
        return HttpResponse(status=404)

    content_type, _ = mimetypes.guess_type(video_path)
    content_type = content_type or 'video/mp4'

    # Using a context-independent open to prevent premature closing
    file_handle = open(video_path, 'rb')
    response = RangedFileResponse(request, file_handle, content_type=content_type)

    # Explicitly set headers to help Ubuntu Chrome
    response['Content-Type'] = content_type
    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = 'inline'

    return response


def check_course_completion(user, course):
    """Determines if a student has finished all requirements for a course."""
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_lessons = LessonCompletion.objects.filter(student=user, lesson__module__course=course).count()

    total_quizzes = Quiz.objects.filter(course=course).count()
    passed_quizzes = QuizSubmission.objects.filter(student=user, quiz__course=course, passed=True).count()

    if total_lessons > 0 and completed_lessons >= total_lessons and passed_quizzes >= total_quizzes:
        enrollment = Enrollment.objects.filter(student=user, course=course).first()
        if enrollment and not enrollment.is_completed:
            enrollment.is_completed = True
            enrollment.save()
            return True
    return False


# --- STUDENT VIEWS ---

def course_list_view(request):
    """Displays all published courses with category, level, and search filtering."""
    courses = Course.objects.filter(is_published=True).select_related('category')
    categories = Category.objects.all()

    category_slug = request.GET.get('category')
    level = request.GET.get('level')
    search_query = request.GET.get('q')

    if category_slug:
        courses = courses.filter(category__slug=category_slug)
    if level:
        courses = courses.filter(level=level)
    if search_query:
        courses = courses.filter(title__icontains=search_query)

    context = {
        'courses': courses,
        'categories': categories,
        'selected_category': category_slug,
        'selected_level': level,
        'levels': Course.LEVEL_CHOICES,
    }
    return render(request, 'courses/course_list.html', context)


def course_detail_view(request, slug):
    """Detailed overview of a course and its curriculum."""
    course = get_object_or_404(Course, slug=slug)
    is_enrolled = False
    progress = 0
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_lesson_ids = []

    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
        if is_enrolled:
            completed_lesson_ids = list(LessonCompletion.objects.filter(
                student=request.user,
                lesson__module__course=course
            ).values_list('lesson_id', flat=True))

            if total_lessons > 0:
                progress = int((len(completed_lesson_ids) / total_lessons) * 100)

    context = {
        'course': course,
        'is_enrolled': is_enrolled,
        'progress': progress,
        'total_lessons': total_lessons,
        'completed_lesson_ids': completed_lesson_ids,
    }
    return render(request, 'courses/course_detail.html', context)


@login_required
@require_POST
def enroll_view(request, slug):
    """Enrolls the user and redirects them to the player."""
    course = get_object_or_404(Course, slug=slug)
    Enrollment.objects.get_or_create(student=request.user, course=course)
    return redirect('course_player', slug=course.slug)


@login_required
def my_courses_view(request):
    """List of courses the user is currently taking."""
    user_enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__category')
    return render(request, 'courses/my_courses.html', {'enrollments': user_enrollments})


@login_required
def course_player_view(request, slug, lesson_id=None):
    """Main learning interface with robust content discovery and progress tracking."""
    course = get_object_or_404(Course, slug=slug)

    if not Enrollment.objects.filter(student=request.user, course=course).exists():
        return redirect('course_detail', slug=slug)

    modules = course.modules.prefetch_related('lessons', 'quizzes').all()

    # robustly find current lesson (scan all modules if none specified)
    if lesson_id:
        current_lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    else:
        current_lesson = None
        for module in modules:
            lesson = module.lessons.order_by('order').first()
            if lesson:
                current_lesson = lesson
                break

    if not current_lesson:
        messages.warning(request, "This course has no lessons available yet.")
        return redirect('course_detail', slug=course.slug)

    # Fetch Progress Data
    completed_lesson_ids = list(LessonCompletion.objects.filter(
        student=request.user, lesson__module__course=course
    ).values_list('lesson_id', flat=True))

    passed_quiz_ids = list(QuizSubmission.objects.filter(
        student=request.user, quiz__course=course, passed=True
    ).values_list('quiz_id', flat=True))

    # Navigation Logic
    all_lessons = list(Lesson.objects.filter(module__course=course).order_by('module__order', 'order'))
    next_lesson = prev_lesson = None
    try:
        idx = all_lessons.index(current_lesson)
        if idx < len(all_lessons) - 1: next_lesson = all_lessons[idx + 1]
        if idx > 0: prev_lesson = all_lessons[idx - 1]
    except ValueError:
        pass

    # YouTube URL Formatting
    if current_lesson.video_url:
        url = current_lesson.video_url
        if "watch?v=" in url:
            current_lesson.video_url = url.replace("watch?v=", "embed/")
        elif "youtu.be/" in url:
            video_id = url.split("/")[-1].split("?")[0]
            current_lesson.video_url = f"https://www.youtube.com/embed/{video_id}"

    total_lessons = len(all_lessons)
    progress = int((len(completed_lesson_ids) / total_lessons) * 100) if total_lessons > 0 else 0

    context = {
        'course': course, 'modules': modules, 'current_lesson': current_lesson,
        'next_lesson': next_lesson, 'prev_lesson': prev_lesson,
        'completed_lesson_ids': completed_lesson_ids,
        'passed_quiz_ids': passed_quiz_ids, 'progress': progress,
        'sidebar_minimized': request.session.get('sidebar_minimized', False),
    }
    return render(request, 'courses/course_player.html', context)


@login_required
def take_quiz_view(request, quiz_id):
    """Assessment logic for grading quizzes and checking course completion."""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    course = quiz.course

    if not Enrollment.objects.filter(student=request.user, course=course).exists():
        return redirect('course_detail', slug=course.slug)

    if QuizSubmission.objects.filter(student=request.user, quiz=quiz, passed=True).exists():
        messages.info(request, "Assessment already passed.")
        return redirect('course_player', slug=course.slug)

    if request.method == 'POST':
        questions = quiz.questions.all()
        total_questions = questions.count()
        correct_answers = 0

        for question in questions:
            selected_id = request.POST.get(f'question_{question.id}')
            if selected_id and Choice.objects.filter(id=selected_id, question=question, is_correct=True).exists():
                correct_answers += 1

        score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0
        passed = score >= course.passing_percentage

        QuizSubmission.objects.create(student=request.user, quiz=quiz, score=score, passed=passed)
        course_completed = check_course_completion(request.user, course) if passed else False

        return render(request, 'courses/quiz_result.html', {
            'quiz': quiz, 'score': score, 'passed': passed,
            'total_questions': total_questions, 'correct_answers': correct_answers,
            'course_completed': course_completed,
        })

    return render(request, 'courses/take_quiz.html', {'quiz': quiz})


@login_required
@require_POST
def mark_lesson_complete(request, lesson_id):
    """AJAX endpoint for marking lesson progress."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    LessonCompletion.objects.get_or_create(student=request.user, lesson=lesson)

    course = lesson.module.course
    course_completed = check_course_completion(request.user, course)

    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_count = LessonCompletion.objects.filter(student=request.user, lesson__module__course=course).count()
    progress_percent = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0

    return JsonResponse({
        'status': 'success',
        'course_completed': course_completed,
        'progress': progress_percent
    })


# --- EDUCATOR MANAGEMENT VIEWS ---

@login_required
def create_course_view(request, slug=None):
    course = get_object_or_404(Course, slug=slug, educator=request.user) if slug else None
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            new_course = form.save(commit=False)
            new_course.educator = request.user
            new_course.save()
            messages.success(request, f"Course {'updated' if course else 'created'} successfully!")
            return redirect('manage_curriculum', slug=new_course.slug)
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/course_form.html',
                  {'form': form, 'course': course, 'action': 'Edit' if course else 'Create'})


@login_required
def manage_curriculum_view(request, slug):
    course = get_object_or_404(Course, slug=slug, educator=request.user)
    modules = course.modules.prefetch_related('lessons', 'quizzes').all()
    return render(request, 'courses/manage_curriculum.html', {'course': course, 'modules': modules})


@login_required
@require_POST
def add_module_view(request, slug):
    course = get_object_or_404(Course, slug=slug, educator=request.user)
    title = request.POST.get('title')
    if title:
        Module.objects.create(course=course, title=title, order=course.modules.count() + 1)
    return redirect('manage_curriculum', slug=slug)


@login_required
@require_POST
def delete_module_view(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__educator=request.user)
    course_slug = module.course.slug
    module.delete()
    return redirect('manage_curriculum', slug=course_slug)


@login_required
def add_lesson_view(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__educator=request.user)
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            lesson.order = module.lessons.count() + 1
            lesson.save()
            return redirect('manage_curriculum', slug=module.course.slug)
    else:
        form = LessonForm()
    return render(request, 'courses/lesson_form.html', {'form': form, 'module': module})


@login_required
def edit_lesson_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__educator=request.user)
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            return redirect('manage_curriculum', slug=lesson.module.course.slug)
    else:
        form = LessonForm(instance=lesson)
    return render(request, 'courses/lesson_form.html',
                  {'form': form, 'module': lesson.module, 'lesson': lesson, 'action': 'Edit'})


@login_required
@require_POST
def delete_lesson_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__educator=request.user)
    course_slug = lesson.module.course.slug
    lesson.delete()
    return redirect('manage_curriculum', slug=course_slug)


@login_required
def create_quiz_view(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__educator=request.user)
    if request.method == 'POST':
        title = request.POST.get('title')
        quiz = Quiz.objects.create(module=module, course=module.course, title=title)
        return redirect('manage_quiz_questions', quiz_id=quiz.id)
    return render(request, 'courses/quiz_form.html', {'module': module})


@login_required
def manage_quiz_questions_view(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, course__educator=request.user)
    questions = quiz.questions.prefetch_related('choices').all()
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        if question_text:
            question = Question.objects.create(quiz=quiz, text=question_text, order=questions.count() + 1)
            for i in range(1, 5):
                choice_text = request.POST.get(f'choice_{i}')
                is_correct = request.POST.get('correct_choice') == str(i)
                if choice_text: Choice.objects.create(question=question, text=choice_text, is_correct=is_correct)
            return redirect('manage_quiz_questions', quiz_id=quiz.id)
    return render(request, 'courses/manage_quiz_questions.html', {'quiz': quiz, 'questions': questions})


@login_required
def edit_question_view(request, question_id):
    question = get_object_or_404(Question, id=question_id, quiz__course__educator=request.user)
    choices = question.choices.all().order_by('id')
    if request.method == 'POST':
        question.text = request.POST.get('question_text')
        question.save()
        for i, choice in enumerate(choices, start=1):
            choice.text = request.POST.get(f'choice_{i}')
            choice.is_correct = request.POST.get('correct_choice') == str(i)
            choice.save()
        return redirect('manage_quiz_questions', quiz_id=question.quiz.id)
    return render(request, 'courses/edit_question.html',
                  {'quiz': question.quiz, 'question': question, 'choices': choices})


@login_required
@require_POST
def delete_question_view(request, question_id):
    question = get_object_or_404(Question, id=question_id, quiz__course__educator=request.user)
    quiz_id = question.quiz.id
    question.delete()
    return redirect('manage_quiz_questions', quiz_id=quiz_id)


@login_required
@require_POST
def reorder_questions_view(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, course__educator=request.user)
    data = json.loads(request.body)
    for index, q_id in enumerate(data.get('order', [])):
        Question.objects.filter(id=q_id, quiz=quiz).update(order=index + 1)
    return JsonResponse({'status': 'success'})


# --- CERTIFICATES ---

@login_required
def download_certificate(request, course_slug):
    enrollment = get_object_or_404(Enrollment, student=request.user, course__slug=course_slug, is_completed=True)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    p.setStrokeColor(HexColor('#2563eb'))
    p.setLineWidth(5)
    p.rect(0.2 * inch, 0.2 * inch, width - 0.4 * inch, height - 0.4 * inch)

    p.setFont("Helvetica-Bold", 40)
    p.drawCentredString(width / 2, height - 2 * inch, "CERTIFICATE OF COMPLETION")

    p.setFont("Helvetica", 18)
    p.drawCentredString(width / 2, height - 2.5 * inch, "This is to certify that")
    p.setFont("Helvetica-Bold", 32)
    p.drawCentredString(width / 2, height - 3.5 * inch, f"{request.user.get_full_name() or request.user.email}")

    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, height - 5 * inch, f"{enrollment.course.title}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'Certificate_{course_slug}.pdf')

@login_required
@require_POST
def toggle_sidebar_preference(request):
    """Saves the user's minimized/maximized sidebar preference to their session context."""
    try:
        data = json.loads(request.body)
        is_minimized = data.get('is_minimized', False)
        request.session['sidebar_minimized'] = is_minimized
        return JsonResponse({'status': 'success', 'sidebar_minimized': is_minimized})
    except Exception:
        return JsonResponse({'status': 'error'}, status=400)