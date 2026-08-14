"""Connection tracing service.

The tracing logic is isolated from the HTTP layer so that it can be tested
independently. ``TopologyTracer`` determines which Connections are associated
with a Site, Device, or Interface.

Each trace matches a Connection when *either* of its endpoint Interfaces
belongs to the traced object. Matching is done at the database level with a
single query and ``distinct()`` so a Connection appears at most once even when
both of its endpoints belong to the traced object.
"""
from django.db.models import Q

from topology.models import Connection


class TopologyTracer:
    @staticmethod
    def _base_queryset():
        return Connection.objects.select_related(
            'start_interface__device__site',
            'end_interface__device__site',
        )

    @classmethod
    def trace_interface(cls, interface):
        """Connections where the given Interface is the start or end endpoint."""
        return (
            cls._base_queryset()
            .filter(Q(start_interface=interface) | Q(end_interface=interface))
            .distinct()
            .order_by('id')
        )

    @classmethod
    def trace_device(cls, device):
        """Connections where either endpoint Interface belongs to the Device."""
        return (
            cls._base_queryset()
            .filter(Q(start_interface__device=device) | Q(end_interface__device=device))
            .distinct()
            .order_by('id')
        )

    @classmethod
    def trace_site(cls, site):
        """Connections where either endpoint Interface belongs to a Device in the Site."""
        return (
            cls._base_queryset()
            .filter(Q(start_interface__device__site=site) | Q(end_interface__device__site=site))
            .distinct()
            .order_by('id')
        )
