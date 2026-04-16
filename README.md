# Bitrix Taxi Router

Минимальный живой каркас Bitrix24-приложения. Проект сохраняет install flow, локальный запуск, деплой и пустой UI-холст для дальнейшей разработки.

## Что осталось

- FastAPI backend с обязательными маршрутами Bitrix;
- хранение установленных порталов и токенов в SQLite;
- минимальная install-страница для завершения установки через `BX24.installFinish()`;
- пустой белый UI-экран по маршруту `/ui/groups`;
- текущий Docker/Fly deploy flow без смены точки входа.

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python3 run.py init-db
python3 run.py serve
```

## Деплой на Fly.io

- приложение слушает `8080`;
- health-check остается на `/health`;
- SQLite хранится в `/data/bitrix_taxi_router.sqlite3`, поэтому для прод-окружения нужен volume;
- перед деплоем проверьте значение `app = "..."` в `fly.toml`.

## Основные маршруты

- `GET /health` — health-check для локального запуска и Fly;
- `GET` / `POST /install` — минимальный install flow Bitrix;
- `GET` / `POST /install/callback` — технический маршрут установки;
- `GET` / `POST /ui/groups` — пустой белый UI-холст;
- `GET /` — такой же минимальный пустой экран.

## Спецификации

- [`distribution_deals_spec.md`](distribution_deals_spec.md) — подробное описание раздела `Распределение сделок`, его полей и логики работы перед реализацией.
