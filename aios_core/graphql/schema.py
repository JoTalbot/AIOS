import strawberry
from typing import List, Optional

@strawberry.type
class TemplateType:
    id: str
    name: str
    intent: str
    platform: Optional[str]

@strawberry.type
class Query:
    @strawberry.field
    def templates(self) -> List[TemplateType]:
        return [
            TemplateType(id="1", name="Greeting", intent="greeting", platform="olx"),
            TemplateType(id="2", name="Price", intent="price_inquiry", platform=None)
        ]

schema = strawberry.Schema(query=Query)
