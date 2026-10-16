import json
import re

from django.test import TestCase

from account.models import Version


class DataJsViewTests(TestCase):
    def test_data_js_returns_executable_json_assignments(self):
        version = Version.objects.create(
            application=Version.ApplicationType.WINDOWS,
            version="1.0.0",
            image="image_version/screenshot.png",
            description='A "quoted" release </script>',
            file="file_version/app.zip",
        )

        response = self.client.get("/chat/data.js")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/javascript")
        content = response.content.decode()
        platforms_json = re.search(r"window\.PLATFORMS = (.*);", content).group(1)
        versions_json = re.search(r"window\.VERSIONS = (.*);", content).group(1)
        self.assertEqual(json.loads(platforms_json)["windows"], "Dark.Talk Windows")
        self.assertEqual(
            json.loads(versions_json),
            [
                {
                    "id": version.id,
                    "application": "windows",
                    "version": "1.0.0",
                    "image": version.image.url,
                    "description": 'A "quoted" release </script>',
                    "file": version.file.url,
                }
            ],
        )
