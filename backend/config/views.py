import logging

from django.db import Error, connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            connection.ensure_connection()
        except Error:
            logger.exception("Health check: banco de dados indisponível")
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ok"})


health = HealthView.as_view()
