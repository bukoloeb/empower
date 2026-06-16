from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Category, Course, Module, Lesson, Quiz, Question, Choice, Resource
# Import your Custom User model
from users.models import User


# --- USER ADMIN FIX ---
# This fixes the "Unknown field(s) (username)" error
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    ordering = ('email',)

    # We redefine fieldsets to remove any reference to 'username'
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'profile_picture')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Used when creating a user in admin
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name'),
        }),
    )


# Unregister the default and register our fix
# Note: This usually goes in users/admin.py, but included here for completeness
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)


# --- COURSE & CONTENT ADMIN ---

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


class ModuleInline(admin.StackedInline):
    model = Module
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'educator', 'level', 'is_published')
    list_filter = ('category', 'level', 'is_published')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    inlines = [LessonInline]


# Register remaining models
admin.site.register(Category)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(Resource)