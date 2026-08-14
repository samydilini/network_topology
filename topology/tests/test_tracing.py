"""Tests for the connection tracing service and the /api/trace/ endpoint.

Shared topology built by ``TopologyFixtureMixin``::

    site_a
      ├── dev_a1  (if_a1_1, if_a1_2)
      └── dev_a2  (if_a2_1)
    site_b
      └── dev_b1  (if_b1_1)
    site_empty
      └── dev_empty (if_empty)          # no connections

    CONN0001  if_a1_1 <-> if_a1_2       # both endpoints on dev_a1 / site_a
    CONN0002  if_a1_1 <-> if_a2_1       # dev_a1 <-> dev_a2, both in site_a
    CONN0003  if_a2_1 <-> if_b1_1       # site_a <-> site_b
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from topology.models import Connection, Device, Interface, Site
from topology.services.tracer import TopologyTracer


class TopologyFixtureMixin:
    def setUp(self):
        super().setUp()
        self.site_a = Site.objects.create(name='Site A', status='Active')
        self.site_b = Site.objects.create(name='Site B', status='Active')
        self.site_empty = Site.objects.create(name='Site Empty', status='Active')

        self.dev_a1 = Device.objects.create(name='dev-a1', site=self.site_a, serial_number='SN-A1')
        self.dev_a2 = Device.objects.create(name='dev-a2', site=self.site_a, serial_number='SN-A2')
        self.dev_b1 = Device.objects.create(name='dev-b1', site=self.site_b, serial_number='SN-B1')
        self.dev_empty = Device.objects.create(name='dev-empty', site=self.site_empty, serial_number='SN-E1')

        self.if_a1_1 = Interface.objects.create(name='Gi0/1', device=self.dev_a1, speed=1000, status='Up')
        self.if_a1_2 = Interface.objects.create(name='Gi0/2', device=self.dev_a1, speed=1000, status='Up')
        self.if_a2_1 = Interface.objects.create(name='Gi0/1', device=self.dev_a2, speed=1000, status='Up')
        self.if_b1_1 = Interface.objects.create(name='Gi0/1', device=self.dev_b1, speed=1000, status='Up')
        self.if_empty = Interface.objects.create(name='Gi0/1', device=self.dev_empty, speed=1000, status='Up')

        self.c_intra = Connection.objects.create(
            connection_id='CONN0001', status='Connected',
            start_interface=self.if_a1_1, end_interface=self.if_a1_2,
        )
        self.c_cross_dev = Connection.objects.create(
            connection_id='CONN0002', status='Connected',
            start_interface=self.if_a1_1, end_interface=self.if_a2_1,
        )
        self.c_cross_site = Connection.objects.create(
            connection_id='CONN0003', status='Connected',
            start_interface=self.if_a2_1, end_interface=self.if_b1_1,
        )


def ids(queryset_or_list):
    return sorted(obj.id for obj in queryset_or_list)


class TopologyTracerServiceTests(TopologyFixtureMixin, TestCase):
    def test_interface_trace_matches_start_or_end(self):
        # if_a2_1 is the end of CONN0002 and the start of CONN0003.
        result = list(TopologyTracer.trace_interface(self.if_a2_1))
        self.assertEqual(ids(result), ids([self.c_cross_dev, self.c_cross_site]))

    def test_interface_trace_no_connections(self):
        self.assertEqual(list(TopologyTracer.trace_interface(self.if_empty)), [])

    def test_device_trace_spans_multiple_interfaces_and_dedupes(self):
        # dev_a1 owns if_a1_1 and if_a1_2; CONN0001 uses both but must appear once.
        result = list(TopologyTracer.trace_device(self.dev_a1))
        self.assertEqual(ids(result), ids([self.c_intra, self.c_cross_dev]))
        self.assertEqual(len(result), len(set(c.id for c in result)))

    def test_site_trace_spans_multiple_devices_and_dedupes(self):
        result = list(TopologyTracer.trace_site(self.site_a))
        self.assertEqual(ids(result), ids([self.c_intra, self.c_cross_dev, self.c_cross_site]))
        self.assertEqual(len(result), 3)

    def test_site_trace_empty(self):
        self.assertEqual(list(TopologyTracer.trace_site(self.site_empty)), [])

    def test_results_are_ordered_by_id(self):
        result_ids = [c.id for c in TopologyTracer.trace_site(self.site_a)]
        self.assertEqual(result_ids, sorted(result_ids))


class TraceAPITests(TopologyFixtureMixin, APITestCase):
    url = '/api/trace/'

    def trace(self, **params):
        return self.client.get(self.url, params)

    def connection_ids(self, response):
        return sorted(c['connection_id'] for c in response.data['connections'])

    def test_trace_interface_via_either_endpoint(self):
        response = self.trace(type='interface', id=self.if_a2_1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['traced_object'],
                         {'type': 'interface', 'id': self.if_a2_1.id, 'name': self.if_a2_1.name})
        self.assertEqual(response.data['connections_count'], 2)
        self.assertEqual(self.connection_ids(response), ['CONN0002', 'CONN0003'])

    def test_trace_device_dedupes_shared_connection(self):
        response = self.trace(type='device', id=self.dev_a1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['connections_count'], 2)
        self.assertEqual(self.connection_ids(response), ['CONN0001', 'CONN0002'])

    def test_trace_site_spans_devices(self):
        response = self.trace(type='site', id=self.site_a.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['connections_count'], 3)
        self.assertEqual(self.connection_ids(response), ['CONN0001', 'CONN0002', 'CONN0003'])

    def test_count_matches_connections_length(self):
        response = self.trace(type='site', id=self.site_a.id)
        self.assertEqual(response.data['connections_count'], len(response.data['connections']))

    def test_no_duplicate_connections(self):
        response = self.trace(type='site', id=self.site_a.id)
        returned = [c['id'] for c in response.data['connections']]
        self.assertEqual(len(returned), len(set(returned)))

    def test_connections_use_target_representation(self):
        response = self.trace(type='interface', id=self.if_a1_1.id)
        connection = response.data['connections'][0]
        self.assertIn('start_target', connection)
        self.assertIn('end_target', connection)
        self.assertNotIn('start_interface', connection)

    def test_empty_trace_result(self):
        response = self.trace(type='site', id=self.site_empty.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['connections_count'], 0)
        self.assertEqual(response.data['connections'], [])

    def test_missing_type_returns_400(self):
        response = self.trace(id=self.site_a.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_id_returns_400(self):
        response = self.trace(type='site')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_type_returns_400(self):
        response = self.trace(type='router', id=self.site_a.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_integer_id_returns_400(self):
        response = self.trace(type='device', id='abc')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_object_returns_404(self):
        response = self.trace(type='device', id=99999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
