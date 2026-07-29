import yaml
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse


class OpenAPIExporter:
    def __init__(self, app: FastAPI):
        self.app = app

    def get_spec(self) -> dict:
        return get_openapi(
            title=self.app.title, version=self.app.version, routes=self.app.routes, description=self.app.description
        )

    def as_json(self) -> JSONResponse:
        return JSONResponse(self.get_spec())

    def as_yaml(self):
        spec = self.get_spec()
        yaml_content = yaml.dump(spec, default_flow_style=False, allow_unicode=True)
        from fastapi.responses import Response

        return Response(content=yaml_content, media_type="application/x-yaml")


exporter = None


def init_exporter(app: FastAPI):
    global exporter
    exporter = OpenAPIExporter(app)
    return exporter
