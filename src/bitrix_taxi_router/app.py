from __future__ import annotations

from fastapi import FastAPI

from .api.event_routes import register_event_routes
from .api.install_routes import register_install_routes
from .api.ui_routes import register_ui_routes
from .database import Database
from .service import PortalService
from .settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    effective_settings = settings or Settings.load()
    effective_settings.ensure_runtime_dirs()

    database = Database(effective_settings.db_path)
    database.init_schema()
    service = PortalService(database)

    app = FastAPI(title="Bitrix Taxi Router")
    app.state.settings = effective_settings
    app.state.database = database
    app.state.portal_service = service

    register_ui_routes(app, service=service, settings=effective_settings)
    register_event_routes(app, service=service)
    register_install_routes(app, service=service, settings=effective_settings)

    return app
