import os
import sys
sys.path.insert(0, "/app")
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hc.settings")
django.setup()

import json
from datetime import timedelta as td
from django.test import Client
from django.utils.timezone import now
from hc.api.models import Check
from hc.test import BaseTestCase


class SummaryAuthTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        if not self.project.api_key_readonly:
            self.project.api_key_readonly = "R" * 32
            self.project.save()

    def test_requires_auth(self):
        r = self.client.get("/api/v1/summary/")
        self.assertEqual(r.status_code, 401)

    def test_readonly_key_allowed(self):
        r = self.client.get(
            "/api/v1/summary/",
            HTTP_X_API_KEY=self.project.api_key_readonly,
        )
        self.assertEqual(r.status_code, 200)

    def test_readwrite_key_allowed(self):
        r = self.client.get(
            "/api/v1/summary/",
            HTTP_X_API_KEY=self.project.api_key,
        )
        self.assertEqual(r.status_code, 200)


class SummaryResponseShapeTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def _get(self):
        return self.client.get(
            "/api/v1/summary/",
            HTTP_X_API_KEY=self.project.api_key,
        )

    def test_returns_200(self):
        r = self._get()
        self.assertEqual(r.status_code, 200)

    def test_response_is_json(self):
        r = self._get()
        self.assertEqual(r["Content-Type"], "application/json")

    def test_response_has_total_key(self):
        r = self._get()
        data = json.loads(r.content)
        self.assertIn("total", data)

    def test_response_has_all_status_keys(self):
        r = self._get()
        data = json.loads(r.content)
        for key in ("up", "down", "grace", "paused", "new"):
            self.assertIn(key, data, f"Missing key: {key}")

    def test_empty_project_all_zeros(self):
        r = self._get()
        data = json.loads(r.content)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["up"], 0)
        self.assertEqual(data["down"], 0)
        self.assertEqual(data["paused"], 0)
        self.assertEqual(data["new"], 0)


class SummaryCountTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def _get(self):
        return self.client.get(
            "/api/v1/summary/",
            HTTP_X_API_KEY=self.project.api_key,
        )

    def test_counts_new_checks(self):
        Check.objects.create(project=self.project, status="new")
        Check.objects.create(project=self.project, status="new")
        data = json.loads(self._get().content)
        self.assertEqual(data["new"], 2)
        self.assertEqual(data["total"], 2)

    def test_counts_paused_checks(self):
        Check.objects.create(project=self.project, status="paused")
        data = json.loads(self._get().content)
        self.assertEqual(data["paused"], 1)

    def test_counts_down_checks(self):
        Check.objects.create(project=self.project, status="down")
        data = json.loads(self._get().content)
        self.assertEqual(data["down"], 1)

    def test_counts_up_checks(self):
        c = Check.objects.create(project=self.project, status="up")
        c.last_ping = now()
        c.timeout = td(hours=1)
        c.save()
        data = json.loads(self._get().content)
        self.assertEqual(data["up"], 1)

    def test_total_matches_sum_of_statuses(self):
        Check.objects.create(project=self.project, status="new")
        Check.objects.create(project=self.project, status="paused")
        Check.objects.create(project=self.project, status="down")
        data = json.loads(self._get().content)
        status_sum = data["up"] + data["down"] + data["grace"] + data["paused"] + data["new"]
        self.assertEqual(data["total"], status_sum)

    def test_mixed_statuses(self):
        Check.objects.create(project=self.project, status="new")
        Check.objects.create(project=self.project, status="new")
        Check.objects.create(project=self.project, status="paused")
        Check.objects.create(project=self.project, status="down")
        data = json.loads(self._get().content)
        self.assertEqual(data["total"], 4)
        self.assertEqual(data["new"], 2)
        self.assertEqual(data["paused"], 1)
        self.assertEqual(data["down"], 1)


class SummaryIsolationTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        from hc.accounts.models import Project as HcProject
        self.project2 = HcProject.objects.create(owner=self.alice, api_key="W" * 32, name="IsolationProject")

    def test_does_not_count_other_project_checks(self):
        Check.objects.create(project=self.project2, status="down")
        Check.objects.create(project=self.project2, status="paused")
        r = self.client.get(
            "/api/v1/summary/",
            HTTP_X_API_KEY=self.project.api_key,
        )
        data = json.loads(r.content)
        self.assertEqual(data["total"], 0)

    def test_each_project_sees_only_own_checks(self):
        Check.objects.create(project=self.project, status="new")
        Check.objects.create(project=self.project2, status="down")

        r1 = self.client.get("/api/v1/summary/", HTTP_X_API_KEY=self.project.api_key)
        r2 = self.client.get("/api/v1/summary/", HTTP_X_API_KEY=self.project2.api_key)

        d1 = json.loads(r1.content)
        d2 = json.loads(r2.content)

        self.assertEqual(d1["total"], 1)
        self.assertEqual(d1["new"], 1)
        self.assertEqual(d2["total"], 1)
        self.assertEqual(d2["down"], 1)
