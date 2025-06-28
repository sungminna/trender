from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from starlette.middleware.base import BaseHTTPMiddleware
from time import monotonic

import logging
import os
from typing import Optional


DEFAULT_OTLP_ENDPOINT = "localhost:4317"  # Collector gRPC endpoint


def setup_observability(app: Optional[object] = None, db_engine: Optional[object] = None) -> None:
    """Configure OpenTelemetry tracing, metrics, and logging.

    Parameters
    ----------
    app : FastAPI, optional
        FastAPI application instance. If provided, request/response
        tracing middleware is injected automatically.
    db_engine : sqlalchemy.Engine, optional
        SQLAlchemy engine instance. SQLAlchemy queries will be traced if
        provided.
    """
    # ------------------------------------------------------------------
    # Resource Attributes (service name etc.)
    # ------------------------------------------------------------------
    service_name = os.getenv("OTEL_SERVICE_NAME", "lgraph")
    resource = Resource.create({SERVICE_NAME: service_name})

    # ------------------------------------------------------------------
    # Traces
    # ------------------------------------------------------------------
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    span_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", DEFAULT_OTLP_ENDPOINT),
        insecure=True,
    )
    span_processor = BatchSpanProcessor(span_exporter)
    trace_provider.add_span_processor(span_processor)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    metric_exporter = OTLPMetricExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", DEFAULT_OTLP_ENDPOINT),
        insecure=True,
    )
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------
    # Logs: only output to stdout for Promtail; OTLP log exporter disabled
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # ------------------------------------------------------------------
    # Instrumentations
    # ------------------------------------------------------------------
    if app is not None:
        # FastAPIInstrumentor automatically instruments ASGI (Starlette)
        FastAPIInstrumentor.instrument_app(app)

    # Outbound HTTP requests
    RequestsInstrumentor().instrument()

    # SQLAlchemy
    if db_engine is not None:
        try:
            SQLAlchemyInstrumentor().instrument(engine=db_engine)
        except Exception as exc:  # pragma: no cover
            logging.getLogger(__name__).warning(
                "SQLAlchemy instrumentation failed: %s", exc
            )

    # ------------------------------------------------------------------
    # Request / Response Logging Middleware
    # ------------------------------------------------------------------
    if app is not None:
        class _RequestLoggingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                start_time = monotonic()
                response = await call_next(request)
                duration = monotonic() - start_time

                logging.getLogger("request").info(
                    "HTTP %s %s %s %.3fs",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration,
                    extra={
                        "http.method": request.method,
                        "http.target": request.url.path,
                        "http.status_code": response.status_code,
                        "duration": duration,
                    },
                )
                return response

        # Insert as the first middleware to capture raw duration
        app.add_middleware(_RequestLoggingMiddleware)

    logging.getLogger(__name__).info("OpenTelemetry observability configured.")
