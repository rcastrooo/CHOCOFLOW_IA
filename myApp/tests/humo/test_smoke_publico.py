from django.test import TestCase
from django.urls import reverse


class SmokePublicoTests(TestCase):

    def test_index_carga_correctamente(self):

        response = self.client.get(
            reverse('index')
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_login_carga_correctamente(self):

        response = self.client.get(
            reverse('login')
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_registro_carga_correctamente(self):

        response = self.client.get(
            reverse('registro')
        )

        self.assertEqual(
            response.status_code,
            200
        )