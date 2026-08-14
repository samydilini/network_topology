from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Connection, Device, Interface, Site

# connection_id is a unique alphanumeric identifier (e.g. CONN1002).
CONNECTION_ID_REGEX = r'^[A-Za-z0-9]+$'


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ['id', 'name', 'description', 'status']


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'name', 'site', 'serial_number']


class InterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interface
        fields = ['id', 'name', 'device', 'speed', 'status']


class ConnectionWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Connections.

    Endpoints are supplied as flat Interface primary keys. The Site and Device
    for each endpoint are derived from the Interface and are not part of the
    request.
    """

    connection_id = serializers.RegexField(
        CONNECTION_ID_REGEX,
        max_length=50,
        validators=[UniqueValidator(queryset=Connection.objects.all())],
        help_text='Unique alphanumeric identifier (e.g. CONN1002).',
    )

    class Meta:
        model = Connection
        fields = ['id', 'connection_id', 'name', 'status', 'start_interface', 'end_interface']

    def validate(self, attrs):
        # On update (PUT) both endpoints are always present; on create they are
        # required by the model. Guard with .get to stay defensive either way.
        start = attrs.get('start_interface')
        end = attrs.get('end_interface')
        if start is not None and end is not None and start == end:
            raise serializers.ValidationError(
                'start_interface and end_interface must reference different interfaces.'
            )
        return attrs


class _NamedRefSerializer(serializers.Serializer):
    """An {id, name} reference to a Site, Device, or Interface."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class EndpointTargetSerializer(serializers.Serializer):
    """The complete {site, device, interface} hierarchy for one endpoint."""

    site = _NamedRefSerializer()
    device = _NamedRefSerializer()
    interface = _NamedRefSerializer()


class ConnectionReadSerializer(serializers.ModelSerializer):
    """Serializer for reading Connections.

    Exposes each endpoint as the derived {site, device, interface} hierarchy so
    consumers do not need additional requests to resolve endpoint context.
    """

    start_target = serializers.SerializerMethodField()
    end_target = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = ['id', 'connection_id', 'name', 'status', 'start_target', 'end_target']

    @staticmethod
    def _endpoint(interface):
        device = interface.device
        site = device.site
        return {
            'site': {'id': site.id, 'name': site.name},
            'device': {'id': device.id, 'name': device.name},
            'interface': {'id': interface.id, 'name': interface.name},
        }

    @extend_schema_field(EndpointTargetSerializer)
    def get_start_target(self, obj):
        return self._endpoint(obj.start_interface)

    @extend_schema_field(EndpointTargetSerializer)
    def get_end_target(self, obj):
        return self._endpoint(obj.end_interface)


class TracedObjectSerializer(serializers.Serializer):
    """The object a trace request was run against."""

    type = serializers.ChoiceField(choices=['site', 'device', 'interface'])
    id = serializers.IntegerField()
    name = serializers.CharField()


class TraceResponseSerializer(serializers.Serializer):
    """Response body for the connection tracing endpoint."""

    traced_object = TracedObjectSerializer()
    connections_count = serializers.IntegerField()
    connections = ConnectionReadSerializer(many=True)
