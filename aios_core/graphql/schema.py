
import strawberry


@strawberry.type
class TemplateType:
    id: str
    name: str
    intent: str
    platform: str | None

@strawberry.type
class Query:
    @strawberry.field
    def templates(self) -> list[TemplateType]:
        return [
            TemplateType(id="1", name="Greeting", intent="greeting", platform="olx"),
            TemplateType(id="2", name="Price", intent="price_inquiry", platform=None)
        ]

schema = strawberry.Schema(query=Query)
