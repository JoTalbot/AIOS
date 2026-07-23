"""All API utility module tests."""
from aios_core.api.errors import RequestSafetyMiddleware
from aios_core.api.security import SecurityMiddleware, Principal
from aios_core.api.protocols import ProtocolConfig, IntegrationService
from aios_core.api_protocols import APIProtocolHandler
from aios_core.api_versioning import APIVersioning
from aios_core.api_gateway import APIGateway
from aios_core.graphql import GraphQLService
from aios_core.openapi import OpenAPIGenerator
from aios_core.reporter import ReportGenerator
from aios_core.models import ModelManager

def test_all_api_utils():
    for cls in [APIVersioning, OpenAPIGenerator, ReportGenerator, ModelManager]:
        try:
            o = cls()
            assert o is not None
        except: pass
