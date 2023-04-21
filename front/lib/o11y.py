import os
from opentelemetry import trace, propagate
from opentelemetry.propagators.aws import AwsXRayPropagator
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.sdk.extension.aws.resource.ecs import AwsEcsResourceDetector
from opentelemetry.sdk.resources import get_aggregated_resources
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
from opentelemetry.instrumentation.requests import RequestsInstrumentor

endpoint = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT', '0.0.0.0:4317')
otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.set_tracer_provider(
    TracerProvider(
        sampler=ALWAYS_ON,
        resource=get_aggregated_resources(
            [ AwsEcsResourceDetector() ]
        ),
        active_span_processor=span_processor,
        id_generator=AwsXRayIdGenerator(),
    )
)
propagate.set_global_textmap(AwsXRayPropagator())

RequestsInstrumentor().instrument()

tracer = trace.get_tracer('front')