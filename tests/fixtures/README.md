# Sanitized test fixtures

Shared pytest fixtures in `tests/conftest.py` create temporary PNG anchors, a provider-neutral fake
image provider, fake Runway SDK responses, fake output URLs/downloads, generation requests, and a
completed dry run. This directory intentionally contains no real credentials, authorization
headers, real provider payloads, or generated Lady LaLa images. An autouse fixture rejects socket
connections so every automated test fails immediately if code attempts network access.
