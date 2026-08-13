"""URL configuration for the topology app.

CRUD resources are registered with a DRF router (currently empty; resource
ViewSets are added in later phases). The OpenAPI schema and Swagger UI are
exposed alongside the API routes. All of these are mounted under ``/api/`` by
the project URL configuration.
"""
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]

urlpatterns += router.urls
