# Сайт антикафе «Com!cs»

Django-сайт по ТЗ: карта заведения с бронированием, каталоги настольных и консольных игр,
аренда игр, мероприятия, новости и статистика, панель администратора.
Что делает каждый файл — в `ОПИСАНИЕ_ФАЙЛОВ.txt`.

Демо-версия (только просмотр, без входа и оплаты): https://erekson12nk.github.io/comics-anticafe/
Она собирается автоматически при каждом изменении в ветке main (`.github/workflows/pages.yml`,
команда `python manage.py build_demo`).

## Запуск на своем компьютере (Windows)

```
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_demo
.venv\Scripts\python manage.py runserver
```

Каталог настолок заполняется из списка заведения на Tesera (сохраненная копия, 329 игр).
Чтобы подтянуть свежий список из интернета: `.venv\Scripts\python manage.py import_tesera`.

Откройте http://127.0.0.1:8000/. Демо-администратор: логин `admin`, пароль `comics-admin-2026`
(только для локальной проверки — на сервере сразу смените: `python manage.py changepassword admin`).

## Регулярные задачи (на сервере через cron)

| Когда | Команда | Что делает |
|---|---|---|
| раз в неделю | `python manage.py import_tesera` | добавляет новые игры из списка на Tesera |
| каждый день ночью | `python manage.py update_prices` | обновляет цены настолок с Hobby Games |
| 1-го числа в 00:05 | `python manage.py monthly_top` | публикует топ-15 игр месяца в новостях и обнуляет счетчик |

## Настройки для сервера (переменные окружения)

| Переменная | Зачем |
|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS` | обязательные для боевого сервера |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` | переход с SQLite на PostgreSQL |
| `VK_APP_ID`, `VK_APP_SECRET` | вход через VK ID (без них кнопка VK скрыта) |
| `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` | настоящая оплата (без них — демо-оплата) |

Адрес для уведомлений ЮKassa: `https://<домен>/pay/yookassa/webhook/`.
Адрес возврата для приложения VK: `https://<домен>/social/complete/vk-oauth2/`.

## Тесты

```
.venv\Scripts\python manage.py test tests
```
