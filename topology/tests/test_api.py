"""Smoke tests for the API foundation.

These verify that the DRF stack and OpenAPI plumbing are wired up correctly.
Resource-specific tests are added in later phases.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from topology.models import Site


class SchemaEndpointTests(APITestCase):
    def test_openapi_schema_is_served(self):
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_ui_is_served(self):
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SiteAPITests(APITestCase):
    url = '/api/sites/'

    def setUp(self):
        self.valid_payload = {
            'name': 'London Data Center',
            'description': 'Primary London facility',
            'status': 'Active',
        }

    def detail_url(self, site_id):
        return f'{self.url}{site_id}/'

    def test_create_site(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'London Data Center')
        self.assertEqual(Site.objects.count(), 1)

    def test_list_sites_is_unpaginated(self):
        Site.objects.create(name='S1', status='Active')
        Site.objects.create(name='S2', status='Planned')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # No pagination: the response body is a plain list of sites.
        self.assertEqual(len(response.data), 2)

    def test_retrieve_site(self):
        site = Site.objects.create(name='S1', status='Active')
        response = self.client.get(self.detail_url(site.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], site.id)

    def test_update_site(self):
        site = Site.objects.create(name='S1', status='Active')
        payload = {'name': 'S1-renamed', 'description': '', 'status': 'Planned'}
        response = self.client.put(self.detail_url(site.id), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        site.refresh_from_db()
        self.assertEqual(site.name, 'S1-renamed')
        self.assertEqual(site.status, 'Planned')

    def test_delete_site(self):
        site = Site.objects.create(name='S1', status='Active')
        response = self.client.delete(self.detail_url(site.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Site.objects.filter(id=site.id).exists())

    def test_duplicate_name_rejected(self):
        Site.objects.create(name='London Data Center', status='Active')
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_status_rejected(self):
        payload = {**self.valid_payload, 'status': 'Bogus'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_name_rejected(self):
        payload = {'status': 'Active'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_method_returns_405(self):
        site = Site.objects.create(name='S1', status='Active')
        response = self.client.patch(self.detail_url(site.id), {'name': 'X'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
