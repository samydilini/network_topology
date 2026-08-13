"""Smoke tests for the API foundation.

These verify that the DRF stack and OpenAPI plumbing are wired up correctly.
Resource-specific tests are added in later phases.
"""
from rest_framework import status
from rest_framework.test import APITestCase


class SchemaEndpointTests(APITestCase):
    def test_openapi_schema_is_served(self):
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_ui_is_served(self):
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
