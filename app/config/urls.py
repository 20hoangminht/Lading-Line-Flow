from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health(_request):
    """Liveness probe. Deliberately returns nothing about the customer or their data."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health),
    path("admin/", admin.site.urls),
]
