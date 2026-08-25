from fastapi import APIRouter, Response

from app.core.metrics import metrics

router = APIRouter()


@router.get("")
def get_metrics() -> Response:
    """Telemetry scrape target exporting resource usage in Prometheus format."""
    data = metrics.get_prometheus_metrics()
    return Response(content=data, media_type="text/plain")
