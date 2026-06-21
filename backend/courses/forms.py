from django import forms
from .models import Course, Lesson


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'title', 'category', 'level', 'description',
            'skills_gained', 'estimated_duration', 'thumbnail',
            'provides_certificate', 'passing_percentage', 'is_published'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Shared high-contrast styling classes for non-technical creators
        input_classes = (
            "w-full px-4 py-3 bg-white text-slate-900 font-semibold border-2 border-slate-300 "
            "rounded-xl transition-all outline-none focus:border-blue-600 focus:ring-4 "
            "focus:ring-blue-100 placeholder-slate-400"
        )

        # Assign explicit inputs attributes
        self.fields['title'].widget.attrs.update({
            'class': input_classes, 'placeholder': 'e.g., Introduction to Artificial Intelligence'
        })
        self.fields['category'].widget.attrs.update({
            'class': "w-full px-4 py-3 bg-white text-slate-900 font-semibold border-2 border-slate-300 rounded-xl focus:border-blue-600 focus:ring-4 focus:ring-blue-100"
        })
        self.fields['level'].widget.attrs.update({
            'class': "w-full px-4 py-3 bg-white text-slate-900 font-semibold border-2 border-slate-300 rounded-xl focus:border-blue-600 focus:ring-4 focus:ring-blue-100"
        })
        self.fields['description'].widget.attrs.update({
            'class': input_classes, 'rows': '4',
            'placeholder': 'Provide a comprehensive overview of what the course covers...'
        })
        self.fields['skills_gained'].widget.attrs.update({
            'class': input_classes,
            'placeholder': 'e.g., Prompt Engineering, Data Analysis, Machine Learning (comma separated)'
        })
        self.fields['estimated_duration'].widget.attrs.update({
            'class': input_classes, 'placeholder': '02:30:00'
        })
        self.fields['passing_percentage'].widget.attrs.update({
            'class': "w-32 px-4 py-3 bg-white text-slate-900 font-black border-2 border-slate-300 rounded-xl focus:border-blue-600 text-center",
            'min': '0', 'max': '100', 'placeholder': '80'
        })

        # Style checkboxes and toggle frames safely
        self.fields['provides_certificate'].widget.attrs.update({
            'class': 'w-5 h-5 rounded text-blue-600 focus:ring-blue-500 border-2 border-slate-400 cursor-pointer'
        })
        self.fields['is_published'].widget.attrs.update({
            'class': 'w-5 h-5 rounded text-blue-600 focus:ring-blue-500 border-2 border-slate-400 cursor-pointer'
        })
        self.fields['thumbnail'].widget.attrs.update({
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-black file:uppercase file:tracking-wider file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition-colors cursor-pointer'
        })


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        # Enforce exact match for 'is_preview' right here
        fields = ['title', 'content_type', 'video_url', 'video_file', 'text_content', 'is_preview']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        input_classes = (
            "w-full px-4 py-3 bg-white text-slate-900 font-semibold border-2 border-slate-300 "
            "rounded-xl transition-all outline-none focus:border-blue-600 focus:ring-4 "
            "focus:ring-blue-100 placeholder-slate-400"
        )

        self.fields['title'].widget.attrs.update({
            'class': input_classes, 'placeholder': 'e.g., Introduction to Neural Networks'
        })
        self.fields['content_type'].widget.attrs.update({
            'class': "w-full px-4 py-3 bg-white text-slate-900 font-semibold border-2 border-slate-300 rounded-xl focus:border-blue-600 focus:ring-4 focus:ring-blue-100"
        })
        self.fields['video_url'].widget.attrs.update({
            'class': input_classes, 'placeholder': 'e.g., https://www.youtube.com/watch?v=...'
        })
        self.fields['text_content'].widget.attrs.update({
            'class': input_classes, 'rows': '6',
            'placeholder': 'Write or paste assignment reading layout content right here...'
        })
        self.fields['video_file'].widget.attrs.update({
            'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-black file:uppercase file:tracking-wider file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition-colors cursor-pointer'
        })

        # Connect explicitly to the is_preview checkbox layout
        self.fields['is_preview'].widget.attrs.update({
            'class': 'w-5 h-5 rounded text-blue-600 focus:ring-blue-500 border-2 border-slate-400 cursor-pointer'
        })