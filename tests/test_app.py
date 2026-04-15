from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi.testclient import TestClient

from bitrix_taxi_router.app import create_app
from bitrix_taxi_router.settings import Settings


class AppUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = Settings(
            app_env="test",
            app_host="127.0.0.1",
            app_port=8000,
            db_path=Path(self.temp_dir.name) / "data.sqlite3",
        )
        self.client = TestClient(create_app(self.settings))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_groups_ui_get_embeds_member_id_from_query_string(self) -> None:
        response = self.client.get("/ui/groups?member_id=portal-123")

        self.assertEqual(200, response.status_code)
        self.assertIn('const initialDistributionMemberId = "portal-123";', response.text)

    def test_groups_ui_post_embeds_member_id_from_bitrix_payload(self) -> None:
        response = self.client.post(
            "/ui/groups",
            data={
                "AUTH_ID": "token-1",
                "REFRESH_ID": "refresh-1",
                "DOMAIN": "portal.example.bitrix24.ru",
                "PROTOCOL": "1",
                "MEMBER_ID": "portal-456",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertIn('const initialDistributionMemberId = "portal-456";', response.text)

    def test_groups_ui_contains_bitrix_auth_fallback_and_hidden_grid_rule(self) -> None:
        response = self.client.get("/ui/groups")

        self.assertEqual(200, response.status_code)
        self.assertIn(".reference-grid[hidden]", response.text)
        self.assertIn("BX24.getAuth", response.text)
        self.assertIn("BX24.init", response.text)


if __name__ == "__main__":
    unittest.main()
