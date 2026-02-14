from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models


def assign_existing_notes_to_owner(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    Note = apps.get_model("main", "Note")

    owner = User.objects.order_by("id").first()
    if owner is None:
        username = "legacy_owner"
        i = 1
        while User.objects.filter(username=username).exists():
            i += 1
            username = f"legacy_owner_{i}"
        owner = User.objects.create(username=username, password=make_password(None))

    Note.objects.filter(user__isnull=True).update(user=owner)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0002_assessmentreport"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="note",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="notes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(assign_existing_notes_to_owner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="note",
            name="user",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="notes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
