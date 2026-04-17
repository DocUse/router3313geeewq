from fastapi import FastAPI

from ..service import PortalService
from ..settings import Settings
from .ui_data_routes import register_ui_data_routes
from .ui_page_routes import register_ui_page_routes


def register_ui_routes(app: FastAPI, *, service: PortalService, settings: Settings) -> None:
    register_ui_page_routes(app, service=service, settings=settings)
    register_ui_data_routes(app, service=service, settings=settings)
