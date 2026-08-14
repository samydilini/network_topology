from rest_framework import viewsets

from .models import Device, Interface, Site
from .serializers import DeviceSerializer, InterfaceSerializer, SiteSerializer

# The CRUD ViewSets expose only GET, POST, PUT, and DELETE. Restricting
# ``http_method_names`` keeps this consistent across every resource.
CRUD_METHOD_NAMES = ['get', 'post', 'put', 'delete', 'head', 'options']


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    http_method_names = CRUD_METHOD_NAMES


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    http_method_names = CRUD_METHOD_NAMES


class InterfaceViewSet(viewsets.ModelViewSet):
    queryset = Interface.objects.all()
    serializer_class = InterfaceSerializer
    http_method_names = CRUD_METHOD_NAMES
