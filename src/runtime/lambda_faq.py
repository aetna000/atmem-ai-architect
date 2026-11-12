"""Owned HTTP API v2 entrypoint; no action or provider selected by the request."""
from mangum import Mangum
from public_faq_app import app_factory

handler=Mangum(app_factory(),lifespan='off')
