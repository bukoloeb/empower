from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, LearnerProfile, EducatorProfile, Institution

class CustomUserAdmin(UserAdmin):
    # This determines how the list looks in the admin panel
    list_display = ('email', 'role', 'is_active', 'is_verified', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    ordering = ('email',)
    
    # These sets allow you to edit custom fields (phone, role, etc) in the admin
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'phone_number', 'address', 'is_verified', 'verification_pin')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('role', 'phone_number', 'address')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(LearnerProfile)
admin.site.register(EducatorProfile)
admin.site.register(Institution)