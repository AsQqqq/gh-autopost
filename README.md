# GH AutoPost

Сервис мониторинга коммитов GitHub с публикацией в Telegram-канал.

Отслеживает новые коммиты в приватных репозиториях и публикует их в заданную тему Telegram-канала, а также уведомляет администраторов.

## Возможности

- Мониторинг нескольких репозиториев и веток
- Публикация в конкретную тему (topic) супергруппы/канала Telegram
- Уведомление администраторов после каждой публикации
- Дедупликация коммитов через SQLite
- Пакетная публикация при большом числе новых коммитов
- Фильтрация merge-коммитов
- Классификация коммитов по Conventional Commits
- Дата в московском времени
- Retry с backoff при ошибках GitHub API и Telegram
- Обработка rate-limit GitHub
- Полностью контейнеризован (Docker)

## Структура проекта

```
GH_AUTOPOST/
├── src/
│   ├── main.py            # Точка входа + main loop
│   ├── config.py          # Конфиг из .env
│   ├── storage.py         # SQLite-хранилище
│   ├── github_client.py   # GitHub API
│   ├── formatter.py       # Форматирование сообщений
│   ├── telegram_client.py # Telegram Bot API
│   └── processor.py       # Оркестрация обработки
├── data/                  # SQLite DB (создаётся автоматически, gitignored)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .gitignore
```

## Быстрый старт

### 1. Подготовка конфига

```bash
cp .env.example .env
# Заполните все переменные в .env
```

### 2. Инициализация (первый запуск)

Сохраняет все текущие коммиты в БД **без публикации в Telegram**.
Это нужно сделать один раз, чтобы не засорить канал историческими коммитами.

```bash
docker compose run --rm gh-autopost --save
```

### 3. Основной режим

```bash
docker compose up -d
```

Сервис будет опрашивать GitHub каждые `POLL_INTERVAL` секунд и публиковать только новые коммиты.

## Конфигурация

Все параметры задаются через переменные окружения (файл `.env`).
Шаблон: `.env.example`.

| Переменная              | Описание                                                         | Обязательно |
|-------------------------|------------------------------------------------------------------|-------------|
| `GITHUB_TOKEN`          | GitHub Personal Access Token (scope: `repo`)                     | Да          |
| `REPOS`                 | Репозитории через запятую: `owner/repo1,owner/repo2`             | Да          |
| `BRANCHES`              | Ветки через запятую: `main,develop`                              | Нет (main)  |
| `TELEGRAM_BOT_TOKEN`    | Токен бота от @BotFather                                         | Да          |
| `TELEGRAM_CHANNEL_ID`   | ID канала/супергруппы (напр. `-1001234567890`)                   | Да          |
| `TELEGRAM_TOPIC_ID`     | ID темы в канале (0 — без темы)                                  | Нет (0)     |
| `ADMIN_IDS`             | ID администраторов через запятую                                 | Нет         |
| `POLL_INTERVAL`         | Интервал опроса в секундах                                       | Нет (30)    |
| `BATCH_THRESHOLD`       | Порог пакетной публикации (>=N коммитов — одно сообщение)        | Нет (3)     |
| `FILTER_MERGE_COMMITS`  | Пропускать merge-коммиты (`true`/`false`)                        | Нет (true)  |
| `MAX_COMMITS_PER_RUN`   | Максимум коммитов за один запрос к GitHub                        | Нет (100)   |
| `SIGNATURE`             | Подпись в конце каждого сообщения                                | Нет         |
| `DB_PATH`               | Путь к SQLite-файлу внутри контейнера                            | Нет         |

## Режимы работы

### Init mode (`--save`)

```bash
docker compose run --rm gh-autopost --save
```

Получает все текущие коммиты из репозиториев и сохраняет их в БД. В Telegram ничего не публикуется. Запускается **один раз** перед первым запуском основного режима.

### Основной режим (без флагов)

```bash
docker compose up -d
```

Периодически опрашивает GitHub, находит новые коммиты (которых нет в БД), публикует их в Telegram и сохраняет SHA в БД.

### Debug

```bash
docker compose run --rm gh-autopost --debug
```

## Формат сообщения в Telegram

```
🔔 Новый коммит

📦 Репо: `backend`
🌿 Ветка: `main`
✨ Feature
👤 Автор: Ivan Ivanov
📅 Дата: 17.04.2026 14:32:10 МСК

💬 feat: добавлена авторизация через OAuth

📊 Статистика:
• Файлов изменено: 5
• Добавлено: +120
• Удалено: -34

🔗 Открыть коммит — `a1b2c3d4`

🤖 GH AutoPost
```

## Локальная разработка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/main.py --save   # init
python src/main.py          # normal
python src/main.py --debug  # debug
```

Python 3.12+

## Получение необходимых данных

**GitHub Token**: Settings → Developer settings → Personal access tokens → классический, scope `repo`.

**Telegram Bot**: создайте бота через @BotFather, добавьте в канал как администратора с правом отправки сообщений.

**TELEGRAM_CHANNEL_ID**: перешлите сообщение из канала боту @userinfobot или используйте `getUpdates` через Bot API.

**TELEGRAM_TOPIC_ID**: ID темы виден в URL при открытии темы в веб-версии Telegram.

**ADMIN_IDS**: узнайте свой Telegram ID через @userinfobot.
