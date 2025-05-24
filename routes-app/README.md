# Optimal Routes API

Сервис для оптимизации маршрутов доставки с учетом множества депо и динамического планирования (Multi-Depot Dynamic Vehicle Routing Problem).

## Функциональность

- Управление депо и курьерами
- Обработка заказов
- Оптимизация маршрутов доставки с учетом динамических факторов
- Поддержка множества депо (складов)
- Валидация данных на уровне API и бизнес-логики
- Гибкая настройка через переменные окружения

## Технический стек

- Backend: FastAPI (Python 3.9+)
- База данных: PostgreSQL
- ORM: SQLAlchemy (асинхронный)
- Миграции: Alembic
- Схемы и валидация: Pydantic
- Тестирование: pytest

## Установка и запуск

### Требования

- Python 3.9+
- PostgreSQL 12+
- pip

### Настройка окружения

1. Клонировать репозиторий
2. Создать виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   ```
3. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Создать файл `.env` на основе `.env.example` и настроить переменные окружения
5. Создать базу данных в PostgreSQL

### Миграции

Применить миграции:
```bash
alembic upgrade head
```

Создать новую миграцию:
```bash
alembic revision --autogenerate -m "Описание изменений"
```

### Запуск сервера

Запуск сервера разработки:
```bash
cd routes-app
python main.py
```

Или с использованием uvicorn:
```bash
uvicorn routes-app.main:app --reload
```

## Структура проекта

```
routes-app/
├── api/                  # API endpoints
│   ├── controllers/      # API контроллеры
│   ├── models/           # Модели базы данных
│   ├── schemas/          # Pydantic схемы
│   └── services/         # Сервисные слои (бизнес-логика)
├── core/                 # Ядро приложения
│   ├── config.py         # Конфигурация
│   ├── database.py       # Настройка базы данных
│   └── settings.py       # Загрузка настроек из окружения
├── alembic/              # Миграции Alembic
├── algorithms/           # Алгоритмы оптимизации
│   ├── genetic/          # Генетический алгоритм
│   ├── nearest_neighbor/ # Жадный алгоритм
│   └── ...
├── services/             # Общие сервисы
│   ├── distance/         # Расчет расстояний и маршрутов
│   ├── geocoding/        # Геокодирование
│   └── optimization/     # Оптимизация маршрутов
├── tests/                # Тесты
├── .env.example          # Пример переменных окружения
├── main.py               # Точка входа
├── requirements.txt      # Зависимости
└── README.md             # Документация
```

## Настройка приложения

Основные настройки приложения могут быть заданы через переменные окружения. Все настройки имеют префикс `ROUTES_`. Например:

- `ROUTES_APP_DEBUG=true`: включает режим отладки
- `ROUTES_DB_URL=postgresql+asyncpg://...`: URL подключения к базе данных
- `ROUTES_RUN_PORT=8000`: порт для запуска приложения

Полный список настроек см. в файле `.env.example`.

## API Endpoints

API документация доступна по адресу `/api/docs` или `/api/redoc` после запуска приложения.

Основные группы эндпоинтов:

- `/api/depots`: управление депо
- `/api/couriers`: управление курьерами
- `/api/orders`: управление заказами
- `/api/routes`: управление маршрутами
- `/api/optimization`: оптимизация маршрутов

## Валидация данных

Все входные данные валидируются на нескольких уровнях:

1. Валидация API запросов через Pydantic-схемы
2. Валидация бизнес-логики в сервисных слоях
3. Валидация на уровне базы данных через ограничения SQLAlchemy

Правила валидации включают проверки:
- Форматов данных (телефоны, адреса)
- Диапазонов числовых значений
- Логической согласованности данных
- Уникальности идентификаторов и имен

## Лицензия

Copyright (c) 2023, All rights reserved.

## Optimization Algorithms

The application supports two optimization algorithms for route planning:

1. **OR-Tools Optimizer (Default)**: This uses Google's Operations Research tools, specifically the Vehicle Routing solution, to solve the Multi-Depot Vehicle Routing Problem (MDVRP).

2. **Genetic Algorithm Optimizer**: An alternative implementation that uses evolutionary computation principles to find good solutions. While potentially not as optimal as OR-Tools for some problems, it provides flexibility and customization options.

### Comparing the Optimizers

You can compare the performance and solution quality of both optimizers using the included test scripts:

- `test_standalone.py`: A standalone script that implements simplified versions of both algorithms for direct comparison without dependencies on the API structure.

- `test_genetic_vs_ortools.py`: A more comprehensive test that compares the full implementations as used in the API.

### API Endpoints for Optimization

- **OR-Tools optimization**: `POST /routes/optimize`
- **Genetic Algorithm optimization**: `POST /routes/optimize/genetic`

Both endpoints will return the optimized routes in the same format, making it easy to switch between algorithms or compare results.

### Customizing the Genetic Algorithm

The genetic algorithm can be customized by modifying the parameters in `api/services.py`:

```python
genetic_optimizer = GeneticOptimizer(
    population_size=100,  # Number of solutions in the population
    max_generations=100,  # Maximum iterations of the algorithm
    mutation_rate=0.1,    # Probability of mutating an individual (0-1)
    crossover_rate=0.8,   # Probability of crossing over two individuals (0-1)
    elitism_rate=0.1,     # Proportion of best individuals kept unchanged (0-1)
    timeout_seconds=30    # Maximum time to run in seconds
) 