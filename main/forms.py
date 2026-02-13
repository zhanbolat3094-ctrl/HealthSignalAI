from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .assessment_data import ASSESSMENT_QUESTIONS
from .models import Note


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["title", "content", "is_done"]


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")


class ClinicalAssessmentForm(forms.Form):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
    ]

    DURATION_CHOICES = [
        ("<24h", "Less than 24 hours"),
        ("1-3d", "1-3 days"),
        ("4-7d", "4-7 days"),
        ("1-4w", "1-4 weeks"),
        (">1m", "More than 1 month"),
    ]

    age = forms.IntegerField(min_value=1, max_value=120)
    gender = forms.ChoiceField(choices=GENDER_CHOICES)
    symptom_duration = forms.ChoiceField(choices=DURATION_CHOICES)
    additional_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Optional: timeline, chronic diseases, recent surgery, pregnancy, allergies, etc."}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for idx, question in enumerate(ASSESSMENT_QUESTIONS, start=1):
            self.fields[f"q{idx}"] = forms.CharField(
                label=f"{idx}. {question}",
                required=False,
                widget=forms.Textarea(
                    attrs={
                        "rows": 3,
                        "placeholder": "Write your answer in detail...",
                    }
                ),
            )
