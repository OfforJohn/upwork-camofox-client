# Upwork Camofox Client
- domain_camofox is the only owner of AsyncCamoufox.
- HTTP/API code only validates and dispatches action envelopes.
- AuthGuard validates visible DOM state; it never receives a browser object.
- Save normalized records before advancing cursors.
- Unit tests use a fake Camofox session; real browser tests are opt-in.
- Never use the official Upwork API, sync_playwright, or a CDP launcher.
