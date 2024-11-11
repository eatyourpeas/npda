from django.test import SimpleTestCase, override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF="project.urls")
class CustomErrorHandlerTests(SimpleTestCase):
    def test_error_400(self):
        response = self.client.get("/nonexistent-url/", follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "errors/404.html")

    def test_error_403(self):
        response = self.client.get("/nonexistent-url/", follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "errors/404.html")

    def test_error_404(self):
        response = self.client.get("/nonexistent-url/", follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "errors/404.html")

    def test_error_500(self):
        with self.settings(DEBUG=False):
            response = self.client.get("/nonexistent-url/", follow=True)
            self.assertEqual(response.status_code, 404)
            self.assertTemplateUsed(response, "errors/404.html")

    def test_csrf_fail(self):
        response = self.client.get(reverse("csrf_fail"))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "errors/csrf_fail.html")
