from __future__ import annotations

import json

from .markup import GROUPS_PAGE_MARKUP
from .scripts import GROUPS_PAGE_SCRIPT
from .styles import GROUPS_PAGE_STYLES

GROUPS_PAGE_HEAD = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NaimTech | Распределение</title>
  <script src="//api.bitrix24.tech/api/v1/"></script>
  <style>
"""
GROUPS_PAGE_TAIL = """
  </script>
</body>
</html>
"""


def render_blank_page(*, initial_member_id: str | None = None) -> str:
    initial_member_id_json = json.dumps(initial_member_id or "", ensure_ascii=False)
    template = GROUPS_PAGE_HEAD + GROUPS_PAGE_STYLES + """
  </style>
""" + GROUPS_PAGE_MARKUP + """
  <script>
""" + GROUPS_PAGE_SCRIPT + GROUPS_PAGE_TAIL
    return template.replace("__INITIAL_MEMBER_ID__", initial_member_id_json)
