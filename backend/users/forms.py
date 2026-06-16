from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class UserUpdateForm(forms.ModelForm):
    # This must be a function (def), not a class
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                # Changed text-gray-900 (deep black/gray) and placeholder-gray-400
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition-all bg-white font-medium'
            })

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'profile_picture', 'phone_number', 'address']