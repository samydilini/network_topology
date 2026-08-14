from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Connection, Device, Interface, Site
from .serializers import (
    ConnectionReadSerializer,
    ConnectionWriteSerializer,
    DeviceSerializer,
    InterfaceSerializer,
    SiteSerializer,
    TraceResponseSerializer,
)
from .services.tracer import TopologyTracer

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


# Maps each trace type to its model and the corresponding tracer method.
TRACE_TYPES = {
    'site': (Site, TopologyTracer.trace_site),
    'device': (Device, TopologyTracer.trace_device),
    'interface': (Interface, TopologyTracer.trace_interface),
}


@extend_schema(
    parameters=[
        OpenApiParameter(
            'type', OpenApiTypes.STR, OpenApiParameter.QUERY, required=True,
            enum=list(TRACE_TYPES), description='The kind of object to trace.',
        ),
        OpenApiParameter(
            'id', OpenApiTypes.INT, OpenApiParameter.QUERY, required=True,
            description='Primary key of the object being traced.',
        ),
    ],
    responses={
        200: TraceResponseSerializer,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)
class TraceView(APIView):
    """Trace the Connections associated with a Site, Device, or Interface.

    ``GET /api/trace/?type={site|device|interface}&id={pk}``
    """

    http_method_names = ['get', 'head', 'options']

    def get(self, request):
        type_param = request.query_params.get('type')
        id_param = request.query_params.get('id')

        if not type_param:
            raise ValidationError({'type': 'This query parameter is required.'})
        if type_param not in TRACE_TYPES:
            allowed = ', '.join(TRACE_TYPES)
            raise ValidationError({'type': f'Invalid type. Must be one of: {allowed}.'})
        if id_param is None:
            raise ValidationError({'id': 'This query parameter is required.'})
        try:
            object_id = int(id_param)
        except (TypeError, ValueError):
            raise ValidationError({'id': 'Must be an integer.'})

        model, trace = TRACE_TYPES[type_param]
        try:
            obj = model.objects.get(pk=object_id)
        except model.DoesNotExist:
            raise NotFound(f'No {type_param} found with id {object_id}.')

        connections = trace(obj)
        connection_data = ConnectionReadSerializer(
            connections, many=True, context={'request': request},
        ).data
        data = {
            'traced_object': {'type': type_param, 'id': obj.id, 'name': obj.name},
            'connections_count': len(connection_data),
            'connections': connection_data,
        }
        return Response(data)
