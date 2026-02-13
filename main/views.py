from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404, redirect, render

from .ai_service import build_assessment_payload, generate_assessment_report
from .assessment_data import ASSESSMENT_QUESTIONS
from .forms import ClinicalAssessmentForm, NoteForm, ProfileUpdateForm, SignUpForm
from .models import AssessmentReport, Note


def home(request):
    return render(request, "main/home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "main/signup.html", {"form": form})


@login_required
def note_list(request):
    notes = Note.objects.all()
    return render(request, "main/note_list.html", {"notes": notes})


@login_required
def note_create(request):
    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("note_list")
    else:
        form = NoteForm()
    return render(request, "main/note_form.html", {"form": form, "mode": "create"})


@login_required
def note_update(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return redirect("note_list")
    else:
        form = NoteForm(instance=note)
    return render(request, "main/note_form.html", {"form": form, "mode": "update"})


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.method == "POST":
        note.delete()
        return redirect("note_list")
    return render(request, "main/note_confirm_delete.html", {"note": note})


@login_required
def assessment_test(request):
    if request.method == "POST":
        form = ClinicalAssessmentForm(request.POST)
        if form.is_valid():
            payload = build_assessment_payload(form.cleaned_data)
            report = generate_assessment_report(payload)
            assessment = AssessmentReport.objects.create(
                user=request.user,
                payload=payload,
                ai_report=report,
            )
            context = {
                "report": report,
                "payload": payload,
                "question_count": len(ASSESSMENT_QUESTIONS),
                "assessment": assessment,
            }
            return render(request, "main/assessment_result.html", context)
    else:
        form = ClinicalAssessmentForm()
    return render(
        request,
        "main/assessment_form.html",
        {"form": form, "question_count": len(ASSESSMENT_QUESTIONS)},
    )


@login_required
def profile(request):
    profile_form = ProfileUpdateForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            profile_form = ProfileUpdateForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("profile")
        elif action == "password":
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect("profile")

    context = {
        "profile_form": profile_form,
        "password_form": password_form,
        "assessment_reports": request.user.assessment_reports.all()[:20],
    }
    return render(request, "main/profile.html", context)


@login_required
def report_detail(request, pk):
    report = get_object_or_404(AssessmentReport, pk=pk, user=request.user)
    context = {
        "report_item": report,
    }
    return render(request, "main/report_detail.html", context)
