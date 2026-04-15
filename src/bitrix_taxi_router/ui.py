from __future__ import annotations

import json


def render_blank_page() -> str:
    return """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bitrix App</title>
  <style>
    html, body {
      margin: 0;
      min-height: 100%;
      background: #ffffff;
    }
  </style>
</head>
<body></body>
</html>
"""


def render_install_page(*, initial_member_id: str | None = None) -> str:
    initial_member_id_json = json.dumps(initial_member_id or "", ensure_ascii=False)
    template = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bitrix App Install</title>
  <script src="//api.bitrix24.tech/api/v1/"></script>
  <style>
    html, body {
      margin: 0;
      min-height: 100%;
      background: #ffffff;
    }
  </style>
</head>
<body>
  <script>
    const initialMemberId = __INITIAL_MEMBER_ID__;
    const canvasUrl = initialMemberId ? `/ui/groups?member_id=${encodeURIComponent(initialMemberId)}` : "/ui/groups";

    if (window.BX24 && typeof window.BX24.installFinish === "function") {
      window.BX24.installFinish();
    }

    window.setTimeout(function () {
      window.location.replace(canvasUrl);
    }, 300);
  </script>
</body>
</html>
"""
    return template.replace("__INITIAL_MEMBER_ID__", initial_member_id_json)
