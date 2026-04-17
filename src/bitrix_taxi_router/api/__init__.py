from .event_routes import register_event_routes
from .install_routes import register_install_routes
from .ui_data_routes import register_ui_data_routes
from .ui_page_routes import register_ui_page_routes
from .ui_routes import register_ui_routes

__all__ = [
    "register_event_routes",
    "register_install_routes",
    "register_ui_data_routes",
    "register_ui_page_routes",
    "register_ui_routes",
]
