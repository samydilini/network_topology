from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from topology.models import Site


class SiteModelTests(TestCase):
    def test_str_returns_name(self):
        site = Site.objects.create(name='London Data Center', status=Site.Status.ACTIVE)
        self.assertEqual(str(site), 'London Data Center')

    def test_name_must_be_unique(self):
        Site.objects.create(name='London Data Center', status=Site.Status.ACTIVE)
        with self.assertRaises(IntegrityError):
            Site.objects.create(name='London Data Center', status=Site.Status.PLANNED)

    def test_invalid_status_rejected_on_full_clean(self):
        site = Site(name='Berlin DC', status='Bogus')
        with self.assertRaises(ValidationError):
            site.full_clean()

    def test_valid_statuses_accepted_on_full_clean(self):
        for value in ('Active', 'Planned', 'Decommissioned'):
            site = Site(name=f'Site-{value}', status=value)
            site.full_clean()  # should not raise
