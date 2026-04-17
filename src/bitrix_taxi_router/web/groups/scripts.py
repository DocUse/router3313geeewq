from .script_actions import GROUPS_PAGE_SCRIPT_ACTIONS
from .script_data import GROUPS_PAGE_SCRIPT_DATA
from .script_render import GROUPS_PAGE_SCRIPT_RENDER
from .script_state import GROUPS_PAGE_SCRIPT_STATE


GROUPS_PAGE_SCRIPT = (
    GROUPS_PAGE_SCRIPT_STATE
    + "\n"
    + GROUPS_PAGE_SCRIPT_RENDER
    + "\n"
    + GROUPS_PAGE_SCRIPT_DATA
    + "\n"
    + GROUPS_PAGE_SCRIPT_ACTIONS
)
