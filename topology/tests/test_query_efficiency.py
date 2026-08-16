"""Query-efficiency tests guarding against N+1 patterns.

The asserted query counts are constant and do not grow with the number of
connections, which is what proves ``select_related`` is doing its job.
"""
from rest_framework.test import APITestCase

from topology.models import Connection, Device, Interface, Site


class QueryEfficiencyTests(APITestCase):
    connection_count = 5

    def setUp(self):
        self.site = Site.objects.create(name='Site', status='Active')
        for i in range(self.connection_count):
            dev_a = Device.objects.create(name=f'dev-a-{i}', site=self.site, serial_number=f'SN-A{i}')
            dev_b = Device.objects.create(name=f'dev-b-{i}', site=self.site, serial_number=f'SN-B{i}')
            if_a = Interface.objects.create(name='Gi0/1', device=dev_a, speed=1000, status='Up')
            if_b = Interface.objects.create(name='Gi0/1', device=dev_b, speed=1000, status='Up')
            Connection.objects.create(
                connection_id=f'CONN{i:04d}', status='Connected',
                start_interface=if_a, end_interface=if_b,
            )

    def test_connection_list_is_not_n_plus_1(self):
        # A single query resolves every connection plus its full endpoint
        # hierarchy via select_related.
        with self.assertNumQueries(1):
            response = self.client.get('/api/connections/')
        self.assertEqual(len(response.data), self.connection_count)

    def test_trace_is_not_n_plus_1(self):
        # One query resolves the traced object; one resolves the connections
        # (with their endpoint hierarchy). Constant regardless of match count.
        with self.assertNumQueries(2):
            response = self.client.get('/api/trace/', {'type': 'site', 'id': self.site.id})
        self.assertEqual(response.data['connections_count'], self.connection_count)
