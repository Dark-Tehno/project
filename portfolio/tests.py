from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class PortalViewTests(TestCase):
    @patch("portfolio.views.datetime")
    def test_portal_returns_http_404_outside_birthday(self, mocked_datetime):
        mocked_datetime.today.return_value = datetime(2026, 10, 12)

        response = self.client.get(reverse("portal"))

        self.assertEqual(response.status_code, 404)
