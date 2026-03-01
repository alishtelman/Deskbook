# Backend (MVP)

Базовый API для фазы 1 (MVP): офисы, этажи, рабочие места и бронирования.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API разрешает CORS для локальной разработки фронтенда. Добавлены политики бронирования, которые можно
привязать к офису и отобразить во фронтенде.

## Роли

- Для операций создания офисов/этажей/мест требуется заголовок `X-Role: admin`.
- Бронирование доступно всем пользователям.
- Для рабочих мест с типом `fixed` обязательно указывать `assigned_to`.

## Примеры запросов

```bash
curl -X POST http://localhost:8000/offices \
  -H 'Content-Type: application/json' \
  -H 'X-Role: admin' \
  -d '{"name": "HQ", "address": "Main st."}'

curl -X POST http://localhost:8000/floors \
  -H 'Content-Type: application/json' \
  -H 'X-Role: admin' \
  -d '{"office_id": 1, "name": "1 этаж", "plan_url": "https://cdn.example.com/floor-1.png"}'

curl -X POST http://localhost:8000/desks \
  -H 'Content-Type: application/json' \
  -H 'X-Role: admin' \
  -d '{"floor_id": 1, "label": "A-01", "type": "flex", "zone": "Open Space"}'

curl -X PATCH http://localhost:8000/desks/1 \
  -H 'Content-Type: application/json' \
  -H 'X-Role: admin' \
  -d '{"type": "fixed", "assigned_to": "ivan", "zone": "Team Alpha"}'

curl -X POST http://localhost:8000/reservations \
  -H 'Content-Type: application/json' \
  -d '{"desk_id": 1, "user_id": "ivan", "reservation_date": "2024-08-01", "start_time": "09:00", "end_time": "18:00"}'

curl -X POST http://localhost:8000/policies \
  -H 'Content-Type: application/json' \
  -H 'X-Role: admin' \
  -d '{"name": "Правила HQ", "office_id": 1, "min_days_ahead": 0, "max_days_ahead": 14, "min_duration_minutes": 60, "max_duration_minutes": 540, "no_show_timeout_minutes": 20}'

curl -X DELETE http://localhost:8000/desks/1 \
  -H 'X-Role: admin'
```
