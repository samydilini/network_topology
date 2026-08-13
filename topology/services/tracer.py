"""Connection tracing service.

The tracing logic is isolated from the HTTP layer so that it can be tested
independently. The concrete ``TopologyTracer`` implementation is added in a
later phase; this module currently only marks the service boundary.
"""
