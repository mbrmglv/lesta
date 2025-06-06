# TF-IDF Веб-приложение

Веб-приложение, позволяющее пользователям загружать несколько текстовых файлов, анализировать их с помощью алгоритма TF-IDF и отображать слова, ранжированные по их значениям IDF.

## Возможности

- **Загрузка файлов**: Поддержка нескольких текстовых файлов размером до 5МБ каждый
- **TF-IDF анализ**: Обработка текста для расчета частоты термина и обратной частоты документа
- **Интерактивные результаты**: Отображение результатов в постраничной таблице
- **Современный интерфейс**: Адаптивный дизайн с использованием Tailwind CSS
- **Хранение в базе данных**: Результаты хранятся в базе данных PostgreSQL
- **Контейнеризация**: Настройка Docker и Docker Compose для простого развертывания
- **API документация**: OpenAPI документация для интеграции с другими системами

## API Документация

Приложение предоставляет интерактивную документацию API через OpenAPI:

- Swagger UI: `/docs` - Интерактивное тестирование и документация API
- ReDoc: `/redoc` - Подробная справка по API
- OpenAPI JSON: `/openapi.json` - Исходная OpenAPI схема

## Технологический стек

- **Бэкенд**: FastAPI, Python 3.11, SQLAlchemy, Alembic
- **База данных**: PostgreSQL
- **Фронтенд**: Jinja2 Templates, Tailwind CSS, Alpine.js
- **Обработка текста**: NLTK для токенизации и стоп-слов
- **Тестирование**: Pytest
- **Развертывание**: Docker, Docker Compose

## Запуск приложения

### Использование Docker Compose

Самый простой способ запустить приложение — использовать Docker Compose, который настроит как само приложение, так и базу данных PostgreSQL:

```bash
# Сборка и запуск стека приложений
make docker-compose-up

# Остановка стека приложений
make docker-compose-down

# Просмотр логов
make docker-compose-logs
```

Приложение будет доступно по адресу `http://localhost:8000`.

### Локальная разработка

Для локальной разработки вам потребуется установить и запустить PostgreSQL:

```bash
# Создайте виртуальную среду
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Установка Poetry (если не установлен)
pip install poetry

# Установите зависимости с помощью Poetry
make setup
# или
poetry install --no-root

# Настройте базу данных (измените учетные данные при необходимости)
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tfidf
export SYNC_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tfidf
psql -U postgres -c "CREATE DATABASE tfidf"

# Запустите миграции
make migrate

# Запустите приложение
make run
```

## Управление зависимостями с Poetry

Проект использует Poetry для управления зависимостями. Все пакеты определены в `pyproject.toml`.

```bash
# Добавление новой зависимости
poetry add package_name

# Добавление dev-зависимости
poetry add --group dev package_name

# Обновление зависимостей
poetry update

# Генерация requirements.txt
make requirements
```

Файлы `requirements.txt` и `requirements-dev.txt` автоматически генерируются из `pyproject.toml`.

### Автоматическое обновление requirements.txt

Настроен GitHub Actions workflow, который автоматически обновляет requirements.txt при изменении pyproject.toml:

1. При каждом push в ветку main, если обнаружены изменения в pyproject.toml
2. Workflow можно запустить вручную через GitHub Actions UI
3. Автоматически создается коммит с обновленными файлами

Это гарантирует, что requirements.txt всегда соответствует зависимостям, определенным в pyproject.toml.

## Как это работает

1. **Загрузка**: Пользователи загружают один или несколько текстовых файлов через веб-интерфейс.
2. **Обработка**:
   - Файлы обрабатываются в фоновом режиме
   - Текст токенизируется и нормализуется
   - Слова фильтруются (удаляются стоп-слова)
   - Рассчитываются метрики TF-IDF
   - Результаты сохраняются в базе данных
3. **Результаты**: Слова с наивысшими значениями IDF отображаются в таблице с постраничной навигацией.

## Расчет TF-IDF

- **TF (частота термина)**: Сколько раз слово встречается в тексте
- **DF (частота документа)**: В скольких документах встречается слово
- **IDF (обратная частота документа)**: Log((N+1)/(df+1))+1, где N — количество документов

Приложение обрабатывает каждый загруженный файл как отдельный документ для расчета IDF, что делает анализ более информативным при загрузке нескольких файлов.

## Схема базы данных

- **TextAnalysis**: Хранит информацию о загруженных файлах и статусе их обработки
  - `id`: UUID первичный ключ
  - `filename`: Имя загруженного файла
  - `created_at`: Временная метка загрузки
  - `status`: Статус обработки (processing, completed, failed)
  - `error_message`: Сообщение об ошибке, если обработка не удалась

- **WordResult**: Хранит результаты анализа TF-IDF для каждого слова
  - `id`: Автоинкрементный первичный ключ
  - `analysis_id`: Внешний ключ на TextAnalysis
  - `word`: Анализируемое слово
  - `tf`: Частота термина (количество вхождений)
  - `idf`: Обратная частота документа (оценка значимости)

## Тестирование

```bash
# Запуск тестов
make test

# Запуск с покрытием
make test-cov
```

## Команды для разработки

```bash
# Проверка кода линтерами
make lint

# Создание новой миграции
make migrate-create message="Добавить новое поле"

# Применение миграций
make migrate

# Откат миграций
make migrate-rollback

# Обновление requirements.txt из pyproject.toml
make requirements
```

## Pre-commit хуки

Проект использует pre-commit хуки для автоматического контроля качества кода перед коммитами. Хуки настроены на:

- Удаление лишних пробелов в конце строк
- Добавление пустой строки в конце файлов
- Проверку yaml/toml файлов
- Проверку на наличие отладочных выражений и конфликтов слияния
- Запуск линтера Ruff с автоматическим исправлением
- Форматирование кода с Ruff
- Статическую типизацию с Mypy

## Лицензия

[MIT License](LICENSE)
