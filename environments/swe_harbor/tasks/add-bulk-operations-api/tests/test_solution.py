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


class BulkOperationsAuthTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def _post(self, payload, key=None):
        return self.client.post(
            "/api/v1/checks/bulk/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=key or self.project.api_key,
        )

    def test_requires_auth(self):
        r = self.client.post(
            "/api/v1/checks/bulk/",
            data=json.dumps({"checks": [], "action": "pause"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_get_not_allowed(self):
        r = self.client.get(
            "/api/v1/checks/bulk/",
            HTTP_X_API_KEY=self.project.api_key,
        )
        self.assertNotEqual(r.status_code, 200)


class BulkOperationsValidationTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.check = Check.objects.create(project=self.project)

    def _post(self, payload):
        return self.client.post(
            "/api/v1/checks/bulk/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=self.project.api_key,
        )

    def test_missing_action_returns_400(self):
        r = self._post({"checks": [str(self.check.code)]})
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", json.loads(r.content))

    def test_invalid_action_returns_400(self):
        r = self._post({"checks": [str(self.check.code)], "action": "nuke"})
        self.assertEqual(r.status_code, 400)

    def test_missing_checks_returns_400(self):
        r = self._post({"action": "pause"})
        self.assertEqual(r.status_code, 400)

    def test_empty_checks_list_returns_400(self):
        r = self._post({"checks": [], "action": "pause"})
        self.assertEqual(r.status_code, 400)

    def test_checks_not_list_returns_400(self):
        r = self._post({"checks": "not-a-list", "action": "pause"})
        self.assertEqual(r.status_code, 400)

    def test_invalid_uuid_in_checks_returns_400(self):
        r = self._post({"checks": ["not-a-uuid"], "action": "pause"})
        self.assertEqual(r.status_code, 400)


class BulkPauseTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.c1 = Check.objects.create(project=self.project, status="up")
        self.c2 = Check.objects.create(project=self.project, status="up")

    def _post(self, payload):
        return self.client.post(
            "/api/v1/checks/bulk/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=self.project.api_key,
        )

    def test_pause_single_check(self):
        r = self._post({"checks": [str(self.c1.code)], "action": "pause"})
        self.assertEqual(r.status_code, 200)
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.status, "paused")

    def test_pause_multiple_checks(self):
        r = self._post({"checks": [str(self.c1.code), str(self.c2.code)], "action": "pause"})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["updated"], 2)
        self.c1.refresh_from_db()
        self.c2.refresh_from_db()
        self.assertEqual(self.c1.status, "paused")
        self.assertEqual(self.c2.status, "paused")

    def test_pause_returns_updated_count(self):
        r = self._post({"checks": [str(self.c1.code)], "action": "pause"})
        data = json.loads(r.content)
        self.assertEqual(data["updated"], 1)

    def test_pause_returns_not_found_list(self):
        missing = str(uuid.uuid4())
        r = self._post({"checks": [str(self.c1.code), missing], "action": "pause"})
        data = json.loads(r.content)
        self.assertEqual(data["updated"], 1)
        self.assertIn(missing, data["not_found"])


class BulkResumeTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.c1 = Check.objects.create(project=self.project, status="paused")
        self.c2 = Check.objects.create(project=self.project, status="paused")

    def _post(self, payload):
        return self.client.post(
            "/api/v1/checks/bulk/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=self.project.api_key,
        )

    def test_resume_sets_status_to_new(self):
        r = self._post({"checks": [str(self.c1.code)], "action": "resume"})
        self.assertEqual(r.status_code, 200)
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.status, "new")

    def test_resume_multiple(self):
        r = self._post({"checks": [str(self.c1.code), str(self.c2.code)], "action": "resume"})
        data = json.loads(r.content)
        self.assertEqual(data["updated"], 2)


class BulkDeleteTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.c1 = Check.objects.create(project=self.project)
        self.c2 = Check.objects.create(project=self.project)

    def _post(self, payload):
        return self.client.post(
            "/api/v1/checks/bulk/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=self.project.api_key,
        )

    def test_delete_removes_check(self):
        code = str(self.c1.code)
        r = self._post({"checks": [code], "action": "delete"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Check.objects.filter(code=code).exists())

    def test_delete_multiple(self):
        r = self._post({"checks": [str(self.c1.code), str(self.c2.code)], "action": "delete"})
        data = json.loads(r.content)
        self.assertEqual(data["updated"], 2)
        self.assertFalse(Check.objects.filter(project=self.project).exists())

    def test_delete_returns_not_found_for_missing(self):
        missing = str(uuid.uuid4())
        r = self._post({"checks": [missing], "action": "delete"})
        data = json.loads(r.content)
        self.assertEqual(data["updated"], 0)
        self.assertIn(missing, data["not_found"])


class BulkCrossProjectTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        from hc.accounts.models import Project as HcProject
        self.project2 = HcProject.objects.create(owner=self.alice, api_key="Z" * 32, name="OtherProject")
        self.own_check = Check.objects.create(project=self.project)
        self.other_check = Check.objects.create(project=self.project2)

    def _post(self, payload):
        return self.client.post(
            "/api/v1/checks/bulk/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=self.project.api_key,
        )

    def test_cross_project_check_in_not_found(self):
        r = self._post({"checks": [str(self.other_check.code)], "action": "pause"})
        data = json.loads(r.content)
        self.assertEqual(data["updated"], 0)
        self.assertIn(str(self.other_check.code), data["not_found"])

    def test_cross_project_check_not_modified(self):
        self._post({"checks": [str(self.other_check.code)], "action": "pause"})
        self.other_check.refresh_from_db()
        self.assertNotEqual(self.other_check.status, "paused")

    def test_mixed_own_and_other_project(self):
        r = self._post({
            "checks": [str(self.own_check.code), str(self.other_check.code)],
            "action": "pause",
        })
        data = json.loads(r.content)
        self.assertEqual(data["updated"], 1)
        self.assertEqual(len(data["not_found"]), 1)
        self.own_check.refresh_from_db()
        self.assertEqual(self.own_check.status, "paused")
