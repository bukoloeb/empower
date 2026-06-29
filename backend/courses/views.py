import math
import io
import json
import os
import mimetypes
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, FileResponse, HttpResponse
from django.db.models import Count, Q
# ReportLab Imports for Certificates
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER


# Models and Forms
from .models import (
    Course, Lesson, Module, Enrollment,
    LessonCompletion, Category, Quiz,
    Question, Choice, QuizSubmission
)
from .forms import CourseForm, LessonForm
import base64
from django.core.files.base import ContentFile

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
    """Streams locally uploaded course videos using chunk-aware partial content byte ranges."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    print(f"--- DEBUG: Found lesson {lesson_id}. Title: {lesson.title}")

    if not lesson.video_file:
        print(f"--- DEBUG: Lesson {lesson_id} has NO video_file attached in the database.")
        return HttpResponse(status=404)

    # 1. Standard Django Path Evaluation
    video_path = lesson.video_file.path
    print(f"--- DEBUG: Standard evaluation checks path: {video_path}")

    # 2. FIXED FALLBACK: If standard check fails, dynamically scan your actual 'course_videos' directory structure
    if not os.path.exists(video_path):
        filename = os.path.basename(lesson.video_file.name)
        from django.conf import settings
        fallback_path = os.path.join(settings.MEDIA_ROOT, 'course_videos', filename)
        print(f"--- DEBUG: Standard path missing. Running fallback directory scan at: {fallback_path}")

        if os.path.exists(fallback_path):
            video_path = fallback_path
        else:
            print(f"--- DEBUG: FAIL: Video file missing from both standard path and course_videos root track!")
            return HttpResponse(status=404)

    content_type, _ = mimetypes.guess_type(video_path)
    content_type = content_type or 'video/mp4'

    file_handle = open(video_path, 'rb')
    response = RangedFileResponse(request, file_handle, content_type=content_type)

    response['Content-Type'] = content_type
    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = 'inline'

    return response


def check_course_completion(user, course):
    """Determines if a student has finished all requirements for a course."""
    total_lessons = Lesson.objects.filter(module__course=course).count()
    completed_lessons = LessonCompletion.objects.filter(student=user, lesson__module__course=course).count()
    total_quizzes = Quiz.objects.filter(course=course).count()

    passed_quizzes = QuizSubmission.objects.filter(
        student=user,
        quiz__course=course,
        passed=True
    ).values('quiz').distinct().count()

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

    categories = Category.objects.annotate(
        published_course_count=Count('courses', filter=Q(courses__is_published=True))
    ).filter(published_course_count__gt=0)

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
    """Enrolls the user and redirects them straight to the player learning space."""
    course = get_object_or_404(Course, slug=slug)
    Enrollment.objects.get_or_create(student=request.user, course=course)
    return redirect('course_player', slug=course.slug)


@login_required
def my_courses_view(request):
    """Enhanced dashboard containing analytics sidebar and user progress maps."""
    enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__category')

    enrolled_courses_data = []
    completed_courses = []
    pending_courses = []

    for enrollment in enrollments:
        course = enrollment.course
        total_lessons = Lesson.objects.filter(module__course=course).count()
        completed_lessons = LessonCompletion.objects.filter(student=request.user, lesson__module__course=course).count()

        progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        is_finished = enrollment.is_completed or (progress == 100 and total_lessons > 0)

        item = {
            'enrollment': enrollment,
            'course': course,
            'progress': progress,
            'is_completed': is_finished
        }
        enrolled_courses_data.append(item)

        if is_finished:
            completed_courses.append(item)
        else:
            pending_courses.append(item)

    enrolled_ids = enrollments.values_list('course_id', flat=True)
    suggested_courses = Course.objects.filter(is_published=True).exclude(id__in=enrolled_ids).select_related(
        'category')[:4]

    context = {
        'enrolled_courses': enrolled_courses_data,
        'completed_courses': completed_courses,
        'pending_courses': pending_courses,
        'suggested_courses': suggested_courses,
        'total_enrolled_count': len(enrolled_courses_data),
        'completed_count': len(completed_courses),
        'pending_count': len(pending_courses),
    }
    return render(request, 'courses/my_courses.html', context)


@login_required
def course_player_view(request, slug, lesson_id=None):
    """Main learning interface with strict automated sequential gating flow."""
    course = get_object_or_404(Course, slug=slug)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)

    modules = course.modules.prefetch_related('lessons', 'quizzes').all()
    all_lessons = list(Lesson.objects.filter(module__course=course).order_by('module__order', 'order'))

    if not all_lessons:
        messages.warning(request, "This course has no lessons available yet.")
        return redirect('course_detail', slug=course.slug)

    # Fetch completion IDs cleanly matching the student explicitly
    completed_lesson_ids = set(
        LessonCompletion.objects.filter(
            student=request.user,
            lesson__module__course=course
        ).values_list('lesson_id', flat=True)
    )

    passed_quiz_ids = list(QuizSubmission.objects.filter(
        student=request.user, quiz__course=course, passed=True
    ).values_list('quiz_id', flat=True))

    # Resolve active lesson target pointer
    if lesson_id:
        current_lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    else:
        current_spot_id = next((l.id for l in all_lessons if l.id not in completed_lesson_ids), all_lessons[0].id)
        return redirect('course_player', slug=course.slug, lesson_id=current_spot_id)

    # ENFORCE SEQUENTIAL SECURITY GATING WITH DIRECT DATABASE RE-VERIFICATION
    active_idx = all_lessons.index(current_lesson)
    if active_idx > 0:
        previous_lesson = all_lessons[active_idx - 1]

        # Verify directly against database state to bypass model set evaluation lag
        is_prev_completed = LessonCompletion.objects.filter(
            student=request.user,
            lesson=previous_lesson
        ).exists()

        if not is_prev_completed:
            messages.warning(request, f"Please complete the previous lesson '{previous_lesson.title}' before moving forward!")
            fallback_lesson_id = next((l.id for l in all_lessons if l.id not in completed_lesson_ids), all_lessons[0].id)
            return redirect('course_player', slug=course.slug, lesson_id=fallback_lesson_id)

    # Setup sibling navigation flags
    next_lesson = all_lessons[active_idx + 1] if active_idx < len(all_lessons) - 1 else None
    prev_lesson = all_lessons[active_idx - 1] if active_idx > 0 else None

    # Quiz Access logic: fully gated until all lessons are cleared
    all_lessons_completed = len(completed_lesson_ids) >= len(all_lessons)

    # --- DUAL-MEDIA ROUTER: YOUTUBE VS LOCAL MEDIA STREAMS ---
    is_youtube = False
    video_source_url = ""

    if current_lesson.video_url:
        is_youtube = True
        url = current_lesson.video_url
        if "watch?v=" in url:
            video_source_url = url.replace("watch?v=", "embed/")
        elif "youtu.be/" in url:
            video_id = url.split("/")[-1].split("?")[0]
            video_source_url = f"https://www.youtube.com/embed/{video_id}"
        else:
            video_source_url = url

    elif current_lesson.video_file:
        from django.urls import reverse
        # Dynamically matches your name='lesson_video_stream' route pattern passing the current ID
        video_source_url = reverse('lesson_video_stream', kwargs={'lesson_id': current_lesson.id})

    # FIXED INDENTATION: Progress calculations must run dynamically outside the conditional branches
    total_lessons = len(all_lessons)
    progress = int((len(completed_lesson_ids) / total_lessons) * 100) if total_lessons > 0 else 0

    context = {
        'course': course,
        'modules': modules,
        'current_lesson': current_lesson,
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
        'completed_lesson_ids': completed_lesson_ids,
        'passed_quiz_ids': passed_quiz_ids,
        'progress': progress,
        'all_lessons_completed': all_lessons_completed,
        'sidebar_minimized': request.session.get('sidebar_minimized', False),

        # UI Media Toggles
        'is_youtube': is_youtube,
        'video_source_url': video_source_url,
    }
    return render(request, 'courses/course_player.html', context)


@login_required
@require_POST
def mark_lesson_complete(request, lesson_id):
    """UNIFIED API endpoint triggered automatically by JS trackers to record progress."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    enrollment = Enrollment.objects.filter(student=request.user, course=lesson.module.course).first()

    if not enrollment:
        return JsonResponse({'status': 'error', 'message': 'Not enrolled in this course.'}, status=403)

    # Map cleanly to unified student structure attributes
    LessonCompletion.objects.get_or_create(student=request.user, lesson=lesson)
    course_completed = check_course_completion(request.user, lesson.module.course)

    total_lessons = Lesson.objects.filter(module__course=lesson.module.course).count()
    completed_count = LessonCompletion.objects.filter(student=request.user,
                                                      lesson__module__course=lesson.module.course).count()
    progress_percent = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0

    return JsonResponse({
        'status': 'success',
        'course_completed': course_completed,
        'progress': progress_percent,
        'message': 'Progress logged successfully.'
    })


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
    """Generates PDF certificate for completed courses or live educator previews."""
    course = get_object_or_404(Course, slug=course_slug)

    is_preview = request.GET.get('preview') == 'true'

    if is_preview:
        if course.educator != request.user:
            return HttpResponse("Unauthorized preview request.", status=403)
    else:
        enrollment = get_object_or_404(Enrollment, student=request.user, course=course)
        if not enrollment.is_completed:
            is_now_complete = check_course_completion(request.user, course)
            if not is_now_complete:
                messages.error(request, "Course requirements not yet fully cleared.")
                return redirect('course_player', slug=course.slug)
            enrollment.refresh_from_db()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Color Palette Config
    dark_blue = HexColor('#1e293b')
    sky_blue = HexColor('#38bdf8')
    mid_blue = HexColor('#0284c7')
    charcoal = HexColor('#0f172a')
    muted_text = HexColor('#475569')

    # Medal Colors Config
    gold_dark = HexColor('#ca8a04')
    gold_base = HexColor('#eab308')
    gold_light = HexColor('#facc15')

    # ==========================================
    # --- GEOMETRIC BACKGROUND CORNERS ---
    # ==========================================
    tl1 = p.beginPath()
    tl1.moveTo(0, height);
    tl1.lineTo(180, height);
    tl1.lineTo(0, height - 60);
    tl1.close()
    p.setFillColor(dark_blue);
    p.drawPath(tl1, fill=1, stroke=0)

    tl2 = p.beginPath()
    tl2.moveTo(0, height - 30);
    tl2.lineTo(120, height);
    tl2.lineTo(0, height);
    tl2.close()
    p.setFillColor(sky_blue);
    p.drawPath(tl2, fill=1, stroke=0)

    tr1 = p.beginPath()
    tr1.moveTo(width - 150, height);
    tr1.lineTo(width, height - 120);
    tr1.lineTo(width, height);
    tr1.close()
    p.setFillColor(mid_blue);
    p.drawPath(tr1, fill=1, stroke=0)

    tr2 = p.beginPath()
    tr2.moveTo(width - 90, height);
    tr2.lineTo(width, height - 200);
    tr2.lineTo(width, height);
    tr2.close()
    p.setFillColor(sky_blue);
    p.drawPath(tr2, fill=1, stroke=0)

    bl1 = p.beginPath()
    bl1.moveTo(0, 0);
    bl1.lineTo(220, 0);
    bl1.lineTo(0, 110);
    bl1.close()
    p.setFillColor(dark_blue);
    p.drawPath(bl1, fill=1, stroke=0)

    bl2 = p.beginPath()
    bl2.moveTo(0, 0);
    bl2.lineTo(150, 0);
    bl2.lineTo(0, 160);
    bl2.close()
    p.setFillColor(mid_blue);
    p.drawPath(bl2, fill=1, stroke=0)

    br1 = p.beginPath()
    br1.moveTo(width - 320, 0);
    br1.lineTo(width, 40);
    br1.lineTo(width, 0);
    br1.close()
    p.setFillColor(dark_blue);
    p.drawPath(br1, fill=1, stroke=0)

    br2 = p.beginPath()
    br2.moveTo(width - 180, 0);
    br2.lineTo(width, 90);
    br2.lineTo(width, 0);
    br2.close()
    p.setFillColor(mid_blue);
    p.drawPath(br2, fill=1, stroke=0)

    # ==========================================
    # --- DYNAMIC VECTOR GOLD MEDAL ROSETTE ---
    # ==========================================
    medal_x = width - 150
    medal_y = height - 140

    p.setFillColor(gold_base)
    r1 = p.beginPath()
    r1.moveTo(medal_x - 10, medal_y - 20);
    r1.lineTo(medal_x - 35, medal_y - 95);
    r1.lineTo(medal_x - 15, medal_y - 80);
    r1.lineTo(medal_x + 5, medal_y - 20);
    r1.close()
    p.drawPath(r1, fill=1, stroke=0)

    r2 = p.beginPath()
    r2.moveTo(medal_x - 5, medal_y - 20);
    r2.lineTo(medal_x + 15, medal_y - 80);
    r2.lineTo(medal_x + 35, medal_y - 95);
    r2.lineTo(medal_x + 10, medal_y - 20);
    r2.close()
    p.drawPath(r2, fill=1, stroke=0)

    num_points = 32
    outer_r = 46
    inner_r = 38
    pleat_path = p.beginPath()
    for i in range(num_points * 2):
        angle = i * (math.pi / num_points)
        curr_r = outer_r if i % 2 == 0 else inner_r
        px = medal_x + curr_r * math.cos(angle)
        py = medal_y + curr_r * math.sin(angle)
        if i == 0:
            pleat_path.moveTo(px, py)
        else:
            pleat_path.lineTo(px, py)
    pleat_path.close()
    p.setFillColor(gold_light);
    p.setStrokeColor(gold_dark);
    p.setLineWidth(1)
    p.drawPath(pleat_path, fill=1, stroke=1)

    p.setFillColor(gold_base);
    p.circle(medal_x, medal_y, 34, fill=1, stroke=1)
    p.setFillColor(gold_light);
    p.circle(medal_x, medal_y, 30, fill=1, stroke=0)
    p.setStrokeColor(gold_dark);
    p.setLineWidth(0.75);
    p.circle(medal_x, medal_y, 26, fill=0, stroke=1)

    # ==========================================
    # --- TYPOGRAPHY TEXT GRID ---
    # ==========================================
    # ==========================================
    # --- TYPOGRAPHY TEXT GRID ---
    # ==========================================
    p.setFont("Times-Bold", 42)
    p.setFillColor(charcoal)
    p.drawCentredString(width / 2, height - 130, "Certificate of Completion")

    p.setFont("Helvetica", 14)
    p.setFillColor(muted_text)
    p.drawCentredString(width / 2, height - 190, "This certificate is proudly awarded to")

    if is_preview:
        student_name = "SAMPLE STUDENT NAME"
    else:
        student_name = request.user.get_full_name() or request.user.username or request.user.email

    # Defensive String Width Evaluation to prevent long names from clipping
    student_name = student_name.upper()
    font_size = 28
    max_allowed_width = 460
    name_width = p.stringWidth(student_name, "Helvetica-Bold", font_size)
    if name_width > max_allowed_width:
        font_size = int(font_size * (max_allowed_width / name_width))

    p.setFont("Helvetica-Bold", font_size)
    p.setFillColor(charcoal)
    p.drawCentredString(width / 2, height - 250, student_name)

    p.setStrokeColor(HexColor('#94a3b8'))
    p.setLineWidth(0.75)
    p.line(width / 2 - 180, height - 265, width / 2 + 180, height - 265)

    # --- FULLY DYNAMIC PARAGRAPH-FLOW MIXED STYLE ATTESTATION ---
    attestation_style = ParagraphStyle(
        name='AttestationStyle',
        fontName='Helvetica-Oblique',
        fontSize=11,
        leading=18,
        textColor=muted_text,
        alignment=TA_CENTER
    )

    # Pull variables dynamically from the database
    course_title = course.title

    # Dynamically extract secondary partner organization from signature fields
    partner_org = course.secondary_signatory_title if course.secondary_signatory_title else "Partner Institution"

    # Dynamically handle key skills field with defensive fallback protection checks
    key_skills_gained = course.skills_gained if hasattr(course,
                                                        'skills_gained') and course.skills_gained else "specialized operational track parameters"

    # Construct the exact HTML-formatted text block
    raw_html_content = (
        f"For having successfully completed training in a Transformative <b>\"{course_title}\"</b> "
        f"Program under Empower Edge Enterprises Limited in Collaboration with {partner_org}. "
        f"Empowered with practical skills in <b>{key_skills_gained}</b>."
    )

    # Compile the flowable paragraph within a fixed bounding box constraint width
    attestation_paragraph = Paragraph(raw_html_content, attestation_style)

    # Render paragraph layout centered exactly between left/right boundaries
    paragraph_width = 560
    paragraph_x = (width / 2) - (paragraph_width / 2)
    paragraph_y = height - 355

    attestation_paragraph.wrap(paragraph_width, 100)
    attestation_paragraph.drawOn(p, paragraph_x, paragraph_y)

    # ==========================================
    # --- SIGNATURE HOOK LAYOUT OVERLAYS ---
    # ==========================================
    p.setStrokeColor(charcoal)
    p.setLineWidth(1)
    p.line(140, 135, 300, 135)
    if course.secondary_signature_image and os.path.exists(course.secondary_signature_image.path):
        p.drawImage(course.secondary_signature_image.path, 170, 140, width=80, height=45, mask='auto')
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(charcoal)
    p.drawString(140, 118, course.secondary_signatory_name)
    p.setFont("Helvetica", 10)
    p.setFillColor(muted_text)
    p.drawString(140, 104, course.secondary_signatory_title)

    p.line(width - 300, 135, width - 140, 135)
    if course.primary_signature_image and os.path.exists(course.primary_signature_image.path):
        p.drawImage(course.primary_signature_image.path, width - 260, 140, width=80, height=45, mask='auto')
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(charcoal)
    p.drawString(width - 300, 118, course.primary_signatory_name)
    p.setFont("Helvetica", 10)
    p.setFillColor(muted_text)
    p.drawString(width - 300, 104, course.primary_signatory_title)

    # Proportional ImageReader Aspect Calculation to prevent logo stretching
    if course.certificate_logo and os.path.exists(course.certificate_logo.path):
        img_reader = ImageReader(course.certificate_logo.path)
        img_w, img_h = img_reader.getSize()

        max_height = 80.0
        aspect_ratio = img_w / img_h
        render_w = max_height * aspect_ratio
        render_h = max_height

        logo_x = (width / 2) - (render_w / 2)
        p.drawImage(course.certificate_logo.path, logo_x, 115, width=render_w, height=render_h, mask='auto')
    else:
        p.setFont("Helvetica-Bold", 16)
        p.setFillColor(charcoal)
        p.drawCentredString(width / 2, 95, "Empower Edge Enterprises Ltd")

    p.setFont("Helvetica", 9)
    p.setFillColor(mid_blue)
    p.drawCentredString(width / 2, 80, "Educate, Empower, Elevate")

    p.showPage()
    p.save()
    buffer.seek(0)

    disposition = "inline" if is_preview else "attachment"
    return FileResponse(buffer, content_type='application/pdf', as_attachment=(not is_preview),
                        filename=f'Certificate_{course_slug}.pdf')



@login_required
def configure_certificate_view(request, slug):
    """Allows instructors to customize the certificate design context per course with live drawn pads."""
    course = get_object_or_404(Course, slug=slug, educator=request.user)
    from .forms import CertificateTemplateForm

    if request.method == 'POST':
        form = CertificateTemplateForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            updated_course = form.save(commit=False)

            # Extract and process data-URL signatures if present
            primary_data = form.cleaned_data.get('primary_signature_data')
            if primary_data and primary_data.startswith('data:image/png;base64,'):
                format, imgstr = primary_data.split(';base64,')
                ext = format.split('/')[-1]
                updated_course.primary_signature_image.save(
                    f"sig_primary_{course.id}.{ext}",
                    ContentFile(base64.b64decode(imgstr)),
                    save=False
                )

            secondary_data = form.cleaned_data.get('secondary_signature_data')
            if secondary_data and secondary_data.startswith('data:image/png;base64,'):
                format, imgstr = secondary_data.split(';base64,')
                ext = format.split('/')[-1]
                updated_course.secondary_signature_image.save(
                    f"sig_secondary_{course.id}.{ext}",
                    ContentFile(base64.b64decode(imgstr)),
                    save=False
                )

            updated_course.save()
            messages.success(request, f"Certificate layout updates applied successfully!")
            return redirect('manage_curriculum', slug=course.slug)
    else:
        form = CertificateTemplateForm(instance=course)

    return render(request, 'courses/certificate_form.html', {'form': form, 'course': course})


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