from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from topology.models import Device, Interface, Site


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


class InterfaceModelTests(TestCase):
    def setUp(self):
        self.site = Site.objects.create(name='London Data Center', status='Active')
        self.device = Device.objects.create(name='Core-Switch-02', site=self.site, serial_number='SN1')
        self.other_device = Device.objects.create(name='Router-01', site=self.site, serial_number='SN2')

    def test_str_includes_device_and_name(self):
        interface = Interface.objects.create(
            name='Gi0/1', device=self.device, speed=1000, status='Up',
        )
        self.assertEqual(str(interface), 'Core-Switch-02:Gi0/1')

    def test_duplicate_name_on_same_device_rejected(self):
        Interface.objects.create(name='Gi0/1', device=self.device, speed=1000, status='Up')
        with self.assertRaises(IntegrityError):
            Interface.objects.create(name='Gi0/1', device=self.device, speed=1000, status='Up')

    def test_same_name_on_different_devices_allowed(self):
        Interface.objects.create(name='Gi0/1', device=self.device, speed=1000, status='Up')
        # Should not raise: uniqueness is scoped to (device, name).
        Interface.objects.create(name='Gi0/1', device=self.other_device, speed=1000, status='Up')
        self.assertEqual(Interface.objects.filter(name='Gi0/1').count(), 2)

    def test_non_positive_speed_rejected_on_full_clean(self):
        for bad_speed in (0, -1):
            interface = Interface(name=f'Gi-{bad_speed}', device=self.device, speed=bad_speed, status='Up')
            with self.assertRaises(ValidationError):
                interface.full_clean()

    def test_invalid_status_rejected_on_full_clean(self):
        interface = Interface(name='Gi0/9', device=self.device, speed=1000, status='Bogus')
        with self.assertRaises(ValidationError):
            interface.full_clean()

    def test_device_delete_is_protected_when_interfaces_exist(self):
        Interface.objects.create(name='Gi0/1', device=self.device, speed=1000, status='Up')
        with self.assertRaises(ProtectedError):
            self.device.delete()
