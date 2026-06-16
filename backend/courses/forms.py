from django import forms
from .models import Course, Lesson

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'title', 'category', 'level', 'description',
            'skills_gained', 'thumbnail', 'estimated_duration',
            'provides_certificate', 'passing_percentage', 'is_published'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-bold text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-medium text-gray-900'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-bold text-gray-900'
            }),
            'level': forms.Select(attrs={
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-bold text-gray-900'
            }),
            'skills_gained': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-bold text-gray-900',
                'placeholder': 'e.g. Python, SQL, Project Management'
            }),
            'passing_percentage': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-bold text-gray-900'
            }),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            'title', 'content_type', 'video_url', 'video_file',
            'audio_file', 'pdf_file', 'text_content', 'is_preview'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-bold text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
            }),
            'content_type': forms.Select(attrs={
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-bold text-gray-900'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-bold text-gray-900',
                'placeholder': 'Paste YouTube or Vimeo link here'
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-black file:bg-blue-600 file:text-white hover:file:bg-blue-700 transition-colors'
            }),
            'pdf_file': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-black file:bg-red-50 file:text-red-700 hover:file:bg-red-100 transition-colors'
            }),
            'text_content': forms.Textarea(attrs={
                'rows': 8,
                'class': 'w-full rounded-xl border-gray-300 bg-white p-3 text-sm font-medium text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
            }),
            'is_preview': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            }),
        }