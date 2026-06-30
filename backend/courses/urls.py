from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # --- HIGH PRIORITY TECHNICAL ASSETS & AJAX ---
    # ==========================================
    # Moved to the top so slug catch-alls don't intercept resource streams!
    path('video-stream/<int:lesson_id>/', views.lesson_video_stream, name='lesson_video_stream'),
    path('player/toggle-sidebar/', views.toggle_sidebar_preference, name='toggle_sidebar_preference'),
    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),

    # ==========================================
    # --- PUBLIC & STUDENT CATALOGUE VIEWS ---
    # ==========================================
    # Course Catalog: Main landing page for all courses
    path('', views.course_list_view, name='course_list'),

    # Student Enrollments: List of courses the current user is taking
    path('my-learning/', views.my_courses_view, name='my_courses'),

    # --- Learning Interface (The Player) ---
    path('<slug:slug>/learn/', views.course_player_view, name='course_player'),
    path('<slug:slug>/learn/<int:lesson_id>/', views.course_player_view, name='course_player'),

    # Assessments: Student view to take a module quiz
    path('quiz/<int:quiz_id>/take/', views.take_quiz_view, name='take_quiz'),

    # Rewards: Generates PDF certificate for completed courses
    path('<slug:course_slug>/certificate/', views.download_certificate, name='download_certificate'),

    # ==========================================
    # --- EDUCATOR & MANAGEMENT VIEWS ---
    # ==========================================

    # --- Course Orchestration ---
    path('course/create/', views.create_course_view, name='create_course'),
    path('course/<slug:slug>/edit/', views.create_course_view, name='edit_course'),
    path('course/<slug:slug>/curriculum/', views.manage_curriculum_view, name='manage_curriculum'),
    path('course/<slug:slug>/certificate-settings/', views.configure_certificate_view, name='certificate_settings'),

    # --- Module Management ---
    path('course/<slug:slug>/module/add/', views.add_module_view, name='add_module'),
    path('module/<int:module_id>/delete/', views.delete_module_view, name='delete_module'),

    # --- Lesson Management ---
    path('module/<int:module_id>/lesson/add/', views.add_lesson_view, name='add_lesson'),
    path('lesson/<int:lesson_id>/edit/', views.edit_lesson_view, name='edit_lesson'),
    path('lesson/<int:lesson_id>/delete/', views.delete_lesson_view, name='delete_lesson'),
    # High Priority AJAX Sockets
    path('course/<slug:slug>/modules/reorder/', views.reorder_modules_view, name='reorder_modules'),
    path('module/<int:module_id>/lessons/reorder/', views.reorder_lessons_view, name='reorder_lessons'),
    # --- Quiz Builder ---
    path('module/<int:module_id>/quiz/add/', views.create_quiz_view, name='create_quiz'),
    path('quiz/<int:quiz_id>/questions/', views.manage_quiz_questions_view, name='manage_quiz_questions'),
    path('quiz/<int:quiz_id>/reorder/', views.reorder_questions_view, name='reorder_questions'),
    path('quiz/question/<int:question_id>/edit/', views.edit_question_view, name='edit_question'),
    path('quiz/question/<int:question_id>/delete/', views.delete_question_view, name='delete_question'),

    # ==========================================
    # --- LOW PRIORITY CATCH-ALL SLUG LOOKUPS ---
    # ==========================================
    # Kept at the bottom so it only handles actual detail view pages
    path('<slug:slug>/', views.course_detail_view, name='course_detail'),
    path('<slug:slug>/enroll/', views.enroll_view, name='enroll'),
]