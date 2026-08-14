from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Connection, Device, Interface, Site
from .serializers import (
    ConnectionReadSerializer,
    ConnectionWriteSerializer,
    DeviceSerializer,
    InterfaceSerializer,
    SiteSerializer,
)

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


@extend_schema_view(
    list=extend_schema(responses=ConnectionReadSerializer),
    retrieve=extend_schema(responses=ConnectionReadSerializer),
    create=extend_schema(
        request=ConnectionWriteSerializer, responses=ConnectionReadSerializer,
    ),
    update=extend_schema(
        request=ConnectionWriteSerializer, responses=ConnectionReadSerializer,
    ),
)
class ConnectionViewSet(viewsets.ModelViewSet):
    """CRUD for Connections.

    Writes accept flat Interface IDs (``ConnectionWriteSerializer``); reads and
    write responses expose the derived endpoint hierarchy
    (``ConnectionReadSerializer``).
    """

    queryset = Connection.objects.select_related(
        'start_interface__device__site',
        'end_interface__device__site',
    )
    http_method_names = CRUD_METHOD_NAMES

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ConnectionWriteSerializer
        return ConnectionReadSerializer

    def _read_response(self, instance, status_code):
        serializer = ConnectionReadSerializer(instance, context=self.get_serializer_context())
        return Response(serializer.data, status=status_code)

    def create(self, request, *args, **kwargs):
        write = self.get_serializer(data=request.data)
        write.is_valid(raise_exception=True)
        instance = write.save()
        return self._read_response(instance, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        write = self.get_serializer(instance, data=request.data, partial=partial)
        write.is_valid(raise_exception=True)
        instance = write.save()
        return self._read_response(instance, status.HTTP_200_OK)
