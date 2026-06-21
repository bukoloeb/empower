from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # --- PUBLIC & STUDENT VIEWS ---
    # ==========================================

    # Course Catalog: Main landing page for all courses
    path('', views.course_list_view, name='course_list'),
    path('player/toggle-sidebar/', views.toggle_sidebar_preference, name='toggle_sidebar_preference'),
    # Student Enrollments: List of courses the current user is taking
    path('my-learning/', views.my_courses_view, name='my_courses'),

    # Course Landing Page: Overview, syllabus, and enroll button
    path('<slug:slug>/', views.course_detail_view, name='course_detail'),

    # Enrollment Action: POST endpoint to join a course
    path('<slug:slug>/enroll/', views.enroll_view, name='enroll'),

    # --- Learning Interface (The Player) ---

    # Player Home: Starts at the first available lesson
    path('<slug:slug>/learn/', views.course_player_view, name='course_player'),

    # Player Lesson: Loads a specific lesson in the player
    path('<slug:slug>/learn/<int:lesson_id>/', views.course_player_view, name='course_player_lesson'),

    # Completion Tracking: AJAX endpoint to mark a lesson as finished
    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),

    # Assessments: Student view to take a module quiz
    path('quiz/<int:quiz_id>/take/', views.take_quiz_view, name='take_quiz'),

    # Rewards: Generates PDF certificate for completed courses
    path('<slug:course_slug>/certificate/', views.download_certificate, name='download_certificate'),

    # ==========================================
    # --- EDUCATOR & MANAGEMENT VIEWS ---
    # ==========================================

    # --- Course Orchestration ---

    # Create: Main form for new course metadata
    path('course/create/', views.create_course_view, name='create_course'),

    # Edit Metadata: Update title, thumbnail, or description
    path('course/<slug:slug>/edit/', views.create_course_view, name='edit_course'),

    # Builder Home: The drag-and-drop curriculum management hub
    path('course/<slug:slug>/curriculum/', views.manage_curriculum_view, name='manage_curriculum'),

    # --- Module Management ---

    # Add Module: Create a new container within a course
    path('course/<slug:slug>/module/add/', views.add_module_view, name='add_module'),

    # Delete Module: Remove module and all its nested lessons/quizzes
    path('module/<int:module_id>/delete/', views.delete_module_view, name='delete_module'),

    # --- Lesson Management ---

    # Add Lesson: Create new content (Video/PDF/Text) inside a module
    path('module/<int:module_id>/lesson/add/', views.add_lesson_view, name='add_lesson'),
    path('video-stream/<int:lesson_id>/', views.lesson_video_stream, name='lesson_video_stream'),
    # Edit Lesson: Update content or change asset files
    path('lesson/<int:lesson_id>/edit/', views.edit_lesson_view, name='edit_lesson'),

    # Delete Lesson: Remove a specific lesson
    path('lesson/<int:lesson_id>/delete/', views.delete_lesson_view, name='delete_lesson'),

    # --- Quiz Builder ---

    # Initialize Quiz: Create the assessment object for a module
    path('module/<int:module_id>/quiz/add/', views.create_quiz_view, name='create_quiz'),

    # Question Manager: Add/View questions for a specific quiz
    path('quiz/<int:quiz_id>/questions/', views.manage_quiz_questions_view, name='manage_quiz_questions'),

    # Question Reordering: AJAX endpoint for drag-and-drop sorting
    path('quiz/<int:quiz_id>/reorder/', views.reorder_questions_view, name='reorder_questions'),

    # Edit Question: Modify text or change correct choices
    path('quiz/question/<int:question_id>/edit/', views.edit_question_view, name='edit_question'),

    # Delete Question: Remove a specific question from a quiz
    path('quiz/question/<int:question_id>/delete/', views.delete_question_view, name='delete_question'),
]