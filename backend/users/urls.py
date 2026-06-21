from django.urls import path
from .views import (
    register_view,
    verify_pin_view,
    login_view,
    home_view,
    logout_view,
    profile_settings,
    educator_dashboard_view,  # Corrected name from .views
    learner_dashboard
)

urlpatterns = [
    path('register/', register_view, name='register'),
    path('verify-pin/', verify_pin_view, name='verify_pin'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('home/', home_view, name='home'),
    path('settings/', profile_settings, name='profile_settings'),

    # Corrected view function routing maps locally within the users app namespace
    path('dashboard/educator/', educator_dashboard_view, name='educator_dashboard'),
    path('dashboard/learner/', learner_dashboard, name='learner_dashboard'),
]