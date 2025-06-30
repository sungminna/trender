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


# LGTM 스택 전용 엔드포인트 (Docker 환경에서는 host.docker.internal 사용)
LGTM_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")


def setup_observability(app: Optional[object] = None, db_engine: Optional[object] = None) -> None:
    """
    LGTM 스택 전용 OpenTelemetry 설정 (완전 격리)
    - FastAPI, Database, HTTP 요청 등 인프라스트럭처 트레이싱
    - Langfuse는 별도로 super_agent.py에서 CallbackHandler로 처리됨
    - 글로벌 TracerProvider 설정하지 않음으로써 완전한 격리 보장

    Parameters
    ----------
    app : FastAPI, optional
        FastAPI application instance. Infrastructure tracing will be applied.
    db_engine : sqlalchemy.Engine, optional
        SQLAlchemy engine instance. Database queries will be traced to LGTM.
    """
    
    # ------------------------------------------------------------------
    # LGTM 전용 Resource 설정
    # ------------------------------------------------------------------
    service_name = os.getenv("OTEL_SERVICE_NAME", "lgraph")
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.component": "infrastructure",
        "isolation": "lgtm-only"
    })

    # ------------------------------------------------------------------
    # LGTM 전용 TracerProvider (글로벌로 설정하지 않음!)
    # ------------------------------------------------------------------
    lgtm_trace_provider = TracerProvider(resource=resource)
    
    # ⚠️ 핵심: 글로벌 TracerProvider 설정하지 않음!
    # trace.set_tracer_provider(lgtm_trace_provider)  # 이 줄 제거!

    # LGTM 스택으로만 전송하는 exporter
    span_exporter = OTLPSpanExporter(
        endpoint=LGTM_OTLP_ENDPOINT,
        insecure=True,
    )
    span_processor = BatchSpanProcessor(span_exporter)
    lgtm_trace_provider.add_span_processor(span_processor)

    # ------------------------------------------------------------------
    # LGTM 전용 Metrics
    # ------------------------------------------------------------------
    metric_exporter = OTLPMetricExporter(
        endpoint=LGTM_OTLP_ENDPOINT,
        insecure=True,
    )
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # ------------------------------------------------------------------
    # 로그 설정 (stdout → Promtail → Loki)
    # ------------------------------------------------------------------
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)

    # ------------------------------------------------------------------
    # 인프라스트럭처 계측 (LGTM 전용 provider 직접 할당)
    # ------------------------------------------------------------------
    
    # 기존 계측 정리
    _cleanup_existing_instrumentations()
    
    if app is not None:
        # FastAPI를 LGTM 전용 provider로 계측
        FastAPIInstrumentor().instrument_app(
            app, 
            tracer_provider=lgtm_trace_provider
        )
        logging.info("✅ FastAPI instrumented with LGTM-only provider")

    # HTTP 요청을 LGTM 전용 provider로 계측
    RequestsInstrumentor().instrument(tracer_provider=lgtm_trace_provider)
    logging.info("✅ HTTP requests instrumented with LGTM-only provider")

    # SQLAlchemy를 LGTM 전용 provider로 계측
    if db_engine is not None:
        try:
            SQLAlchemyInstrumentor().instrument(
                engine=db_engine,
                tracer_provider=lgtm_trace_provider
            )
            logging.info("✅ SQLAlchemy instrumented with LGTM-only provider")
        except Exception as exc:  # pragma: no cover
            logging.getLogger(__name__).warning(
                "SQLAlchemy instrumentation failed: %s", exc
            )

    # ------------------------------------------------------------------
    # 인프라스트럭처 로깅 미들웨어
    # ------------------------------------------------------------------
    if app is not None:
        class LGTMOnlyLoggingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                start_time = monotonic()
                response = await call_next(request)
                duration = monotonic() - start_time

                logging.getLogger("lgraph.infrastructure.lgtm").info(
                    "HTTP %s %s %s %.3fs",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration,
                    extra={
                        "destination": "lgtm-only",
                        "isolation": "complete",
                        "http.method": request.method,
                        "http.target": request.url.path,
                        "http.status_code": response.status_code,
                        "duration": duration,
                    },
                )
                return response

        app.add_middleware(LGTMOnlyLoggingMiddleware)

    logging.getLogger(__name__).info("🎯 LGTM-only infrastructure observability configured")
    logging.getLogger(__name__).info("🚫 NO global TracerProvider set - complete isolation guaranteed")


def _cleanup_existing_instrumentations():
    """기존 계측을 정리하여 충돌을 방지합니다."""
    try:
        FastAPIInstrumentor().uninstrument()
    except:
        pass
    
    try:
        RequestsInstrumentor().uninstrument()
    except:
        pass
    
    try:
        SQLAlchemyInstrumentor().uninstrument()
    except:
        pass
    
    logging.info("🧹 Existing instrumentations cleaned up")
