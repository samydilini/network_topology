"""Smoke tests for the API foundation.

These verify that the DRF stack and OpenAPI plumbing are wired up correctly.
Resource-specific tests are added in later phases.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from topology.models import Connection, Device, Interface, Site


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

    def test_delete_site_with_devices_returns_409(self):
        site = Site.objects.create(name='S1', status='Active')
        Device.objects.create(name='D1', site=site, serial_number='SN1')
        response = self.client.delete(self.detail_url(site.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Site.objects.filter(id=site.id).exists())


class DeviceAPITests(APITestCase):
    url = '/api/devices/'

    def setUp(self):
        self.site = Site.objects.create(name='London Data Center', status='Active')
        self.valid_payload = {
            'name': 'Core-Switch-02',
            'site': self.site.id,
            'serial_number': 'SN123456789',
        }

    def detail_url(self, device_id):
        return f'{self.url}{device_id}/'

    def create_device(self, **overrides):
        data = {'name': 'D1', 'site': self.site, 'serial_number': 'SN-D1'}
        data.update(overrides)
        return Device.objects.create(**data)

    def test_create_device(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Core-Switch-02')
        self.assertEqual(response.data['site'], self.site.id)

    def test_retrieve_device(self):
        device = self.create_device()
        response = self.client.get(self.detail_url(device.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], device.id)

    def test_update_device(self):
        device = self.create_device()
        payload = {'name': 'D1-renamed', 'site': self.site.id, 'serial_number': 'SN-D1'}
        response = self.client.put(self.detail_url(device.id), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        device.refresh_from_db()
        self.assertEqual(device.name, 'D1-renamed')

    def test_delete_device(self):
        device = self.create_device()
        response = self.client.delete(self.detail_url(device.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Device.objects.filter(id=device.id).exists())

    def test_duplicate_name_rejected(self):
        self.create_device(name='Core-Switch-02', serial_number='SN-OTHER')
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_serial_number_rejected(self):
        self.create_device(name='Other-Device', serial_number='SN123456789')
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_site_rejected(self):
        payload = {**self.valid_payload, 'site': 99999}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_site_rejected(self):
        payload = {'name': 'No-Site', 'serial_number': 'SN-NS'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_device_with_interfaces_returns_409(self):
        device = self.create_device()
        Interface.objects.create(name='Gi0/1', device=device, speed=1000, status='Up')
        response = self.client.delete(self.detail_url(device.id))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Device.objects.filter(id=device.id).exists())


class InterfaceAPITests(APITestCase):
    url = '/api/interfaces/'

    def setUp(self):
        self.site = Site.objects.create(name='London Data Center', status='Active')
        self.device = Device.objects.create(name='Core-Switch-02', site=self.site, serial_number='SN1')
        self.other_device = Device.objects.create(name='Router-01', site=self.site, serial_number='SN2')
        self.valid_payload = {
            'name': 'GigabitEthernet0/24',
            'device': self.device.id,
            'speed': 1000,
            'status': 'Up',
        }

    def detail_url(self, interface_id):
        return f'{self.url}{interface_id}/'

    def create_interface(self, **overrides):
        data = {'name': 'Gi0/1', 'device': self.device, 'speed': 1000, 'status': 'Up'}
        data.update(overrides)
        return Interface.objects.create(**data)

    def test_create_interface(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'GigabitEthernet0/24')
        self.assertEqual(response.data['device'], self.device.id)

    def test_retrieve_interface(self):
        interface = self.create_interface()
        response = self.client.get(self.detail_url(interface.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], interface.id)

    def test_update_interface(self):
        interface = self.create_interface()
        payload = {'name': 'Gi0/1', 'device': self.device.id, 'speed': 10000, 'status': 'Down'}
        response = self.client.put(self.detail_url(interface.id), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        interface.refresh_from_db()
        self.assertEqual(interface.speed, 10000)
        self.assertEqual(interface.status, 'Down')

    def test_delete_interface(self):
        interface = self.create_interface()
        response = self.client.delete(self.detail_url(interface.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Interface.objects.filter(id=interface.id).exists())

    def test_duplicate_name_same_device_rejected(self):
        self.create_interface(name='GigabitEthernet0/24')
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_name_different_device_allowed(self):
        self.create_interface(name='GigabitEthernet0/24')
        payload = {**self.valid_payload, 'device': self.other_device.id}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_nonexistent_device_rejected(self):
        payload = {**self.valid_payload, 'device': 99999}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_speed_rejected(self):
        payload = {**self.valid_payload, 'speed': 0}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_speed_rejected(self):
        payload = {**self.valid_payload, 'speed': -100}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_integer_speed_rejected(self):
        payload = {**self.valid_payload, 'speed': 'fast'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_status_rejected(self):
        payload = {**self.valid_payload, 'status': 'Bogus'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ConnectionAPITests(APITestCase):
    url = '/api/connections/'

    def setUp(self):
        self.site = Site.objects.create(name='London Data Center', status='Active')
        self.device1 = Device.objects.create(name='London-Router-01', site=self.site, serial_number='SN1')
        self.device2 = Device.objects.create(name='Core-Switch-02', site=self.site, serial_number='SN2')
        self.iface1 = Interface.objects.create(name='Gi0/1', device=self.device1, speed=1000, status='Up')
        self.iface2 = Interface.objects.create(name='Gi0/24', device=self.device2, speed=1000, status='Up')
        self.valid_payload = {
            'connection_id': 'CONN1002',
            'name': 'Core Switch Uplink',
            'status': 'Connected',
            'start_interface': self.iface1.id,
            'end_interface': self.iface2.id,
        }

    def detail_url(self, connection_id):
        return f'{self.url}{connection_id}/'

    def create_connection(self, **overrides):
        data = {
            'connection_id': 'CONN0001', 'status': 'Connected',
            'start_interface': self.iface1, 'end_interface': self.iface2,
        }
        data.update(overrides)
        return Connection.objects.create(**data)

    def test_create_connection_returns_target_hierarchy(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Response uses the derived hierarchy, not the flat input IDs.
        self.assertNotIn('start_interface', response.data)
        self.assertEqual(
            response.data['start_target'],
            {
                'site': {'id': self.site.id, 'name': self.site.name},
                'device': {'id': self.device1.id, 'name': self.device1.name},
                'interface': {'id': self.iface1.id, 'name': self.iface1.name},
            },
        )
        self.assertEqual(response.data['end_target']['interface']['id'], self.iface2.id)

    def test_retrieve_connection(self):
        connection = self.create_connection()
        response = self.client.get(self.detail_url(connection.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['connection_id'], 'CONN0001')
        self.assertIn('start_target', response.data)

    def test_update_connection(self):
        connection = self.create_connection()
        payload = {**self.valid_payload, 'connection_id': 'CONN0001', 'status': 'Disconnected'}
        response = self.client.put(self.detail_url(connection.id), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        connection.refresh_from_db()
        self.assertEqual(connection.status, 'Disconnected')
        self.assertIn('start_target', response.data)

    def test_delete_connection(self):
        connection = self.create_connection()
        response = self.client.delete(self.detail_url(connection.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Connection.objects.filter(id=connection.id).exists())

    def test_duplicate_connection_id_rejected(self):
        self.create_connection(connection_id='CONN1002')
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_connection_id_format_rejected(self):
        payload = {**self.valid_payload, 'connection_id': 'CONN-1002'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_start_interface_rejected(self):
        payload = {**self.valid_payload, 'start_interface': 99999}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_end_interface_rejected(self):
        payload = {**self.valid_payload, 'end_interface': 99999}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_start_interface_rejected(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != 'start_interface'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_end_interface_rejected(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != 'end_interface'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_interface_both_endpoints_rejected(self):
        payload = {**self.valid_payload, 'end_interface': self.iface1.id}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_status_rejected(self):
        payload = {**self.valid_payload, 'status': 'Bogus'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_revalidates_distinct_endpoints(self):
        connection = self.create_connection()
        payload = {**self.valid_payload, 'connection_id': 'CONN0001', 'end_interface': self.iface1.id}
        response = self.client.put(self.detail_url(connection.id), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
