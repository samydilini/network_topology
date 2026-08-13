from django.db import models


class Site(models.Model):
    """A physical or logical location that contains network devices."""

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        PLANNED = 'Planned', 'Planned'
        DECOMMISSIONED = 'Decommissioned', 'Decommissioned'

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name
