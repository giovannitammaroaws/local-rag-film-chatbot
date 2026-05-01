from opentelemetry import trace


def init_tracing():
    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from openinference.instrumentation.openai import OpenAIInstrumentor

        exporter = OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        OpenAIInstrumentor().instrument()
        print("Tracing active - Phoenix at http://localhost:6006")
    except Exception:
        print("Phoenix not available - tracing disabled")


# Returns a tracer instance for manual span creation.
def get_tracer() -> trace.Tracer:
    return trace.get_tracer("rag-film-chatbot")
