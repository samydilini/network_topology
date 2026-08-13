from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """DRF exception handler that maps protected-delete failures to 409.

    Foreign keys use ``on_delete=PROTECT``, so deleting a resource that still
    has dependants raises ``ProtectedError``. DRF's default handler does not
    recognise it (it would surface as a 500), so it is translated into a
    ``409 Conflict`` here. All other exceptions fall through to DRF's default
    handling.
    """
    if isinstance(exc, ProtectedError):
        return Response(
            {'detail': 'Cannot delete this resource because other resources depend on it.'},
            status=status.HTTP_409_CONFLICT,
        )
    return exception_handler(exc, context)
