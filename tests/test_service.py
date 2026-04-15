from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bitrix_taxi_router.database import Database
from bitrix_taxi_router.service import PortalService


class PortalServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "data.sqlite3")
        self.database.init_schema()
        self.service = PortalService(self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_install_portal_saves_new_portal(self) -> None:
        result = self.service.install_portal(
            {
                "auth": {
                    "member_id": "portal-1",
                    "domain": "portal.example.bitrix24.ru",
                    "access_token": "token-1",
                    "refresh_token": "refresh-1",
                    "client_endpoint": "https://portal.example.bitrix24.ru/rest/",
                    "server_endpoint": "https://oauth.bitrix24.tech/rest/",
                    "status": "F",
                }
            }
        )

        self.assertEqual(
            {"member_id": "portal-1", "domain": "portal.example.bitrix24.ru", "saved": True},
            result,
        )

        portal = self.service.get_portal("portal-1")
        self.assertEqual("portal.example.bitrix24.ru", portal.domain)
        self.assertEqual("token-1", portal.access_token)
        self.assertEqual("refresh-1", portal.refresh_token)

    def test_install_portal_updates_existing_portal_without_erasing_tokens(self) -> None:
        self.service.install_portal(
            {
                "auth": {
                    "member_id": "portal-1",
                    "domain": "portal.example.bitrix24.ru",
                    "access_token": "token-1",
                    "refresh_token": "refresh-1",
                    "client_endpoint": "https://portal.example.bitrix24.ru/rest/",
                }
            }
        )

        self.service.install_portal(
            {
                "auth": {
                    "member_id": "portal-1",
                    "domain": "portal.example.bitrix24.ru",
                }
            }
        )

        portal = self.service.get_portal("portal-1")
        self.assertEqual("token-1", portal.access_token)
        self.assertEqual("refresh-1", portal.refresh_token)
        self.assertEqual("https://portal.example.bitrix24.ru/rest/", portal.client_endpoint)


if __name__ == "__main__":
    unittest.main()
