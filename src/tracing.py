from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.openai import OpenAIInstrumentor


# Initializes OpenTelemetry + OpenInference instrumentation.
# Sends traces to Phoenix Docker container via HTTP at localhost:6006/v1/traces.
# OpenAIInstrumentor auto-instruments all openai.chat.completions calls,
# producing proper LLM spans that Phoenix displays with prompt/completion/tokens.
def init_tracing():
    exporter = OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    OpenAIInstrumentor().instrument()
    print("Tracing active — Phoenix at http://localhost:6006")


# Returns a tracer instance for manual span creation.
def get_tracer() -> trace.Tracer:
    return trace.get_tracer("cinerag")
