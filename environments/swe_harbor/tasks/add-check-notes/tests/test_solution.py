import os
import sys
sys.path.insert(0, "/app")
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hc.settings")
django.setup()

import json
import uuid
from django.test import Client
from hc.api.models import Check
from hc.test import BaseTestCase


class CheckNotesFieldTests(BaseTestCase):
    def test_notes_field_exists(self):
        check = Check.objects.create(project=self.project)
        self.assertTrue(hasattr(check, "notes"))

    def test_notes_default_is_empty_string(self):
        check = Check.objects.create(project=self.project)
        self.assertEqual(check.notes, "")

    def test_notes_can_be_saved(self):
        check = Check.objects.create(project=self.project, notes="internal note")
        check.refresh_from_db()
        self.assertEqual(check.notes, "internal note")

    def test_notes_in_to_dict_when_not_readonly(self):
        check = Check.objects.create(project=self.project, notes="my note")
        d = check.to_dict(readonly=False)
        self.assertIn("notes", d)
        self.assertEqual(d["notes"], "my note")

    def test_notes_not_in_to_dict_when_readonly(self):
        check = Check.objects.create(project=self.project, notes="secret")
        d = check.to_dict(readonly=True)
        self.assertNotIn("notes", d)


class CheckNotesAPITests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.check = Check.objects.create(project=self.project, notes="")
        # Create a second project for cross-project isolation tests
        from hc.accounts.models import Project as HcProject
        self.project2 = HcProject.objects.create(owner=self.alice, api_key="Y" * 32, name="Project2")

    def _url(self, check=None):
        c = check or self.check
        return f"/api/v1/checks/{c.code}/notes/"

    def _get(self, check=None, key=None):
        return self.client.get(
            self._url(check),
            HTTP_X_API_KEY=key or self.project.api_key,
        )

    def _post(self, payload, check=None, key=None):
        return self.client.post(
            self._url(check),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=key or self.project.api_key,
        )

    def test_get_requires_auth(self):
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 401)

    def test_post_requires_auth(self):
        r = self.client.post(
            self._url(),
            data=json.dumps({"notes": "x"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_get_returns_200(self):
        r = self._get()
        self.assertEqual(r.status_code, 200)

    def test_get_returns_notes_key(self):
        self.check.notes = "hello"
        self.check.save()
        r = self._get()
        data = json.loads(r.content)
        self.assertIn("notes", data)
        self.assertEqual(data["notes"], "hello")

    def test_get_empty_notes(self):
        r = self._get()
        data = json.loads(r.content)
        self.assertEqual(data["notes"], "")

    def test_get_unknown_check_returns_404(self):
        r = self.client.get(
            f"/api/v1/checks/{uuid.uuid4()}/notes/",
            HTTP_X_API_KEY=self.project.api_key,
        )
        self.assertEqual(r.status_code, 404)

    def test_get_cross_project_check_returns_404(self):
        other = Check.objects.create(project=self.project2)
        r = self._get(check=other)
        self.assertEqual(r.status_code, 404)

    def test_post_sets_notes(self):
        r = self._post({"notes": "new note"})
        self.assertEqual(r.status_code, 200)
        self.check.refresh_from_db()
        self.assertEqual(self.check.notes, "new note")

    def test_post_returns_updated_notes(self):
        r = self._post({"notes": "updated"})
        data = json.loads(r.content)
        self.assertEqual(data["notes"], "updated")

    def test_post_overwrites_existing_notes(self):
        self.check.notes = "old"
        self.check.save()
        self._post({"notes": "new"})
        self.check.refresh_from_db()
        self.assertEqual(self.check.notes, "new")

    def test_post_empty_string_clears_notes(self):
        self.check.notes = "something"
        self.check.save()
        self._post({"notes": ""})
        self.check.refresh_from_db()
        self.assertEqual(self.check.notes, "")

    def test_post_missing_notes_key_returns_400(self):
        r = self._post({})
        self.assertEqual(r.status_code, 400)
        data = json.loads(r.content)
        self.assertIn("error", data)

    def test_post_notes_not_string_returns_400(self):
        r = self._post({"notes": 123})
        self.assertEqual(r.status_code, 400)

    def test_post_notes_list_returns_400(self):
        r = self._post({"notes": ["a", "b"]})
        self.assertEqual(r.status_code, 400)

    def test_post_unknown_check_returns_404(self):
        r = self.client.post(
            f"/api/v1/checks/{uuid.uuid4()}/notes/",
            data=json.dumps({"notes": "x"}),
            content_type="application/json",
            HTTP_X_API_KEY=self.project.api_key,
        )
        self.assertEqual(r.status_code, 404)

    def test_post_cross_project_check_returns_404(self):
        other = Check.objects.create(project=self.project2)
        r = self._post({"notes": "x"}, check=other)
        self.assertEqual(r.status_code, 404)

    def test_multiline_notes(self):
        note = "line1\nline2\nline3"
        self._post({"notes": note})
        self.check.refresh_from_db()
        self.assertEqual(self.check.notes, note)


class CheckNotesSpecTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_create_check_with_notes(self):
        r = self.client.post(
            "/api/v1/checks/",
            data=json.dumps({"name": "testnotes", "notes": "created note"}),
            content_type="application/json",
            HTTP_X_API_KEY=self.project.api_key,
        )
        self.assertIn(r.status_code, (200, 201))
        check = Check.objects.get(project=self.project, name="testnotes")
        self.assertEqual(check.notes, "created note")

    def test_update_check_sets_notes(self):
        r = self.client.post(
            "/api/v1/checks/",
            data=json.dumps({"name": "notescheck456", "notes": "my note"}),
            content_type="application/json",
            HTTP_X_API_KEY=self.project.api_key,
        )
        self.assertIn(r.status_code, (200, 201))
        import json as _json
        data = _json.loads(r.content)
        # notes should be in the response
        self.assertIn("notes", data)
        self.assertEqual(data["notes"], "my note")
