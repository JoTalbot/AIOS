"""GraphQL full."""
from aios_core.graphql import GraphQLService
def test(): s=GraphQLService().stats(); assert isinstance(s,dict)
