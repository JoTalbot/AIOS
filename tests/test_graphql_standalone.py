"""GraphQL standalone test."""
from aios_core.graphql import GraphQLService
def test_init(): assert GraphQLService() is not None
