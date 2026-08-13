"""OpenTelemetry tracer setup. Uses the console exporter by default so
the demo has zero external dependencies (spans print to stdout as JSON);
set OTLP_ENDPOINT to also ship traces to a real backend (Jaeger, Tempo,
Grafana Cloud) via the standard OTLP/HTTP protocol — the same
instrumentation code works unchanged either way, which is the point of
using the OpenTelemetry API rather than a vendor SDK directly.
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

SERVICE_NAME = "aegis-rag-pipeline"


def setup_tracing():
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.environ.get("OTLP_ENDPOINT")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME)


tracer = setup_tracing()
