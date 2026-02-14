import re

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


SECTION_ALIASES = {
    "clinical summary": "clinical_summary",
    "most likely conditions (ranked)": "most_likely_conditions",
    "risk stratification": "risk_stratification",
    "recommended diagnostic tests": "recommended_diagnostic_tests",
    "recommended next steps (by urgency)": "recommended_next_steps",
    "what to monitor": "what_to_monitor",
    "red flags requiring immediate escalation": "red_flags",
    "general supportive advice": "general_supportive_advice",
    "what not to do": "what_not_to_do",
}


def _normalize_heading(line: str) -> str:
    cleaned = re.sub(r"^#{1,6}\s*", "", line).strip()
    cleaned = re.sub(r"^\d+\)\s*", "", cleaned).strip().lower()
    return cleaned


def _clean_markdown_for_display(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        line = re.sub(r"^\s*#{1,6}\s*", "", line)
        cleaned_lines.append(line.rstrip())
    return "\n".join(cleaned_lines).strip()


def parse_assessment_sections(report: str) -> dict[str, str]:
    sections = {value: "" for value in SECTION_ALIASES.values()}
    current_key = None
    bucket: list[str] = []

    for raw_line in report.splitlines():
        line = raw_line.rstrip()
        if line.lstrip().startswith("#"):
            heading = _normalize_heading(line)
            next_key = SECTION_ALIASES.get(heading)
            if next_key:
                if current_key is not None:
                    sections[current_key] = _clean_markdown_for_display("\n".join(bucket))
                current_key = next_key
                bucket = []
                continue
        if current_key is not None:
            bucket.append(line)

    if current_key is not None:
        sections[current_key] = _clean_markdown_for_display("\n".join(bucket))

    return sections


def extract_risk_label(risk_text: str) -> tuple[str, int]:
    lower = risk_text.lower()
    if "emergency" in lower:
        return "Emergency", 95
    if "high" in lower:
        return "High Risk", 82
    if "moderate" in lower:
        return "Moderate Risk", 65
    if "low" in lower:
        return "Low Risk", 35
    return "Unclear", 50


def extract_condition_cards(conditions_text: str) -> list[dict[str, str | int]]:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", conditions_text.strip()) if chunk.strip()]
    cards = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        title = re.sub(r"^[-*]\s*", "", lines[0])
        title = re.sub(r"^\d+[.)]\s*", "", title)
        confidence = 50
        joined = " ".join(lines)
        if re.search(r"\bhigh\b", joined, re.IGNORECASE):
            confidence = 82
        elif re.search(r"\bmedium\b|\bmoderate\b", joined, re.IGNORECASE):
            confidence = 60
        elif re.search(r"\blow\b", joined, re.IGNORECASE):
            confidence = 35
        percent_match = re.search(r"(\d{1,3})\s*%", joined)
        if percent_match:
            confidence = max(0, min(100, int(percent_match.group(1))))

        details = _clean_markdown_for_display("\n".join(lines[1:]))
        cards.append(
            {
                "title": title,
                "details": details,
                "confidence": confidence,
            }
        )

    if not cards and conditions_text.strip():
        cards.append(
            {
                "title": "Differential Assessment",
                "details": conditions_text.strip(),
                "confidence": 50,
            }
        )
    return cards[:5]


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
    notes = Note.objects.filter(user=request.user)
    return render(request, "main/note_list.html", {"notes": notes})


@login_required
def note_create(request):
    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            return redirect("note_list")
    else:
        form = NoteForm()
    return render(request, "main/note_form.html", {"form": form, "mode": "create"})


@login_required
def note_update(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
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
    note = get_object_or_404(Note, pk=pk, user=request.user)
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
            sections = parse_assessment_sections(report)
            risk_label, risk_score = extract_risk_label(sections.get("risk_stratification", ""))
            condition_cards = extract_condition_cards(sections.get("most_likely_conditions", ""))
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
                "sections": sections,
                "risk_label": risk_label,
                "risk_score": risk_score,
                "condition_cards": condition_cards,
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
    sections = parse_assessment_sections(report.ai_report)
    risk_label, risk_score = extract_risk_label(sections.get("risk_stratification", ""))
    condition_cards = extract_condition_cards(sections.get("most_likely_conditions", ""))
    context = {
        "report_item": report,
        "sections": sections,
        "risk_label": risk_label,
        "risk_score": risk_score,
        "condition_cards": condition_cards,
    }
    return render(request, "main/report_detail.html", context)
