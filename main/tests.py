from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Note


class NoteIsolationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user1 = user_model.objects.create_user(username="user1", password="pass12345")
        self.user2 = user_model.objects.create_user(username="user2", password="pass12345")

    def test_note_list_shows_only_current_user_notes(self):
        own_note = Note.objects.create(user=self.user1, title="own")
        Note.objects.create(user=self.user2, title="other")

        self.client.login(username="user1", password="pass12345")
        response = self.client.get(reverse("note_list"))

        self.assertEqual(response.status_code, 200)
        notes = list(response.context["notes"])
        self.assertEqual(notes, [own_note])

    def test_user_cannot_update_note_of_another_user(self):
        foreign_note = Note.objects.create(user=self.user2, title="secret")

        self.client.login(username="user1", password="pass12345")
        response = self.client.get(reverse("note_update", args=[foreign_note.pk]))

        self.assertEqual(response.status_code, 404)

    def test_note_create_assigns_current_user(self):
        self.client.login(username="user1", password="pass12345")
        response = self.client.post(
            reverse("note_create"),
            {"title": "new", "content": "body", "is_done": False},
        )

        self.assertEqual(response.status_code, 302)
        created = Note.objects.get(title="new")
        self.assertEqual(created.user_id, self.user1.id)
