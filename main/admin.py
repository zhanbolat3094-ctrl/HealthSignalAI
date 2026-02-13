from django.contrib import admin

from .models import AssessmentReport, Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_done", "created_at")
    list_filter = ("is_done", "created_at")
    search_fields = ("title", "content")


@admin.register(AssessmentReport)
class AssessmentReportAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "ai_report")
