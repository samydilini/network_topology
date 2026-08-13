from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from topology.models import Device, Site


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


class DeviceModelTests(TestCase):
    def setUp(self):
        self.site = Site.objects.create(name='London Data Center', status='Active')

    def test_str_returns_name(self):
        device = Device.objects.create(name='Core-Switch-02', site=self.site, serial_number='SN1')
        self.assertEqual(str(device), 'Core-Switch-02')

    def test_name_must_be_unique(self):
        Device.objects.create(name='Core-Switch-02', site=self.site, serial_number='SN1')
        with self.assertRaises(IntegrityError):
            Device.objects.create(name='Core-Switch-02', site=self.site, serial_number='SN2')

    def test_serial_number_must_be_unique(self):
        Device.objects.create(name='Device-A', site=self.site, serial_number='SN1')
        with self.assertRaises(IntegrityError):
            Device.objects.create(name='Device-B', site=self.site, serial_number='SN1')

    def test_site_delete_is_protected_when_devices_exist(self):
        Device.objects.create(name='Core-Switch-02', site=self.site, serial_number='SN1')
        with self.assertRaises(ProtectedError):
            self.site.delete()
