#  Лабораторная работа №4 - Реализация асинхронного исполнителя задач, обрабатывающего задачи из
очереди с использованием расширяемых обработчиков

## Описание

Реализация высокопроизводительной асинхронной системы обработки задач на базе `asyncio`. Проект демонстрирует использование паттерна Producer-Consumer, работу с асинхронными очередями, управление жизненным циклом через контекстные менеджеры и расширяемую архитектуру обработчиков.

## Основной функционал:

### Асинхронный исполнитель ( AsyncTaskExecutor )
- **Конкурентная обработка**: использование пула воркеров и `asyncio.Queue` для параллельного выполнения задач без блокировки основного потока.
- **Управление ресурсами**: асинхронный контекстный менеджер (`__aenter__`/`__aexit__`) гарантирует корректный запуск и остановку системы.
- **Контракты на базе Protocol**: описание интерфейса `TaskHandler` через протоколы (Duck Typing), что позволяет добавлять новые типы обработчиков без изменения кода исполнителя.
- **Безопасное завершение (Graceful Shutdown)**: остановка воркеров через sentinel-объекты (None) и механизм `SHUTDOWN_TIMEOUT` для предотвращения зависания программы.
- **Централизованное логирование**: мониторинг всех этапов жизненного цикла задачи — от постановки в очередь до завершения или ошибки.
- **Обработка исключений**: оборачивание ошибок в `TaskProcessingError` с сохранением ссылки на задачу и исходную причину сбоя (cause).
- **Сбор метрик**: расчет времени выполнения, сложности и возраста задач в реальном времени.

## Структура репозитория
```
python-lab-4.1/
│
├── src/
│ ├── task.py # Модель Task с дескрипторами
│ ├── executor.py # Асинхронный исполнитель задач
│ ├── handlers.py # Набор обработчиков (Print, Transform, Metrics и др.)
│ ├── descriptors.py # Дескрипторы валидации (ReadOnly, ValidPriority и т.д.)
│ ├── exceptions.py # Иерархия исключений (InvalidHandlerError, TaskProcessingError)
│ └── system.py # Утилиты и контракты источников
│
├── tests/
│ └── test_queue.py # Асинхронные тесты (pytest-asyncio)
│
├── main.py # Точка входа: демонстрация 6 сценариев работы
├── requirements.txt # Зависимости
└── README.md # Описание проекта
```

## Установка и запуск

### 1. Требования
- Python 3.10+ (для синтаксиса `str | int`)
- pytest 7.0.0+

### 2. Установка зависимостей
```
pip install -r requirements.txt
```

### 3. Запуск демонстрации
```
python main.py
```

### 4. Запуск тестов
```
pytest tests.py
```

## Демонстрация работы
```
2026-05-10 02:03:19,377 - INFO - AsyncTaskExecutor demonstration started.

=== Scenario 1: PrintHandler ===
2026-05-10 02:03:19,377 - INFO - Starting executor with 3 workers
2026-05-10 02:03:19,378 - INFO - Handler registered: PrintHandler
2026-05-10 02:03:19,416 - INFO - Print Handler got task - print-00: urgent: fix critical bug
2026-05-10 02:03:19,606 - INFO - All tasks processed
2026-05-10 02:03:19,606 - INFO - Stopping executor...
2026-05-10 02:03:19,606 - INFO - Executor stopped
2026-05-10 02:03:19,607 - INFO - Elapsed: 0.23s

=== Scenario 5: Error handling ===
2026-05-10 02:03:20,671 - INFO - Starting executor with 2 workers
2026-05-10 02:03:21,111 - ERROR - [worker-1] Task processing error: error-07... | ValueError: Too high priority: 8
2026-05-10 02:03:21,114 - INFO - Successfully processed: 7
2026-05-10 02:03:21,114 - INFO - Errors caught: 1
2026-05-10 02:03:21,115 - WARNING -   • error-07 (priority=8): Too high priority: 8

=== Scenario 6: Concurrency check ===
2026-05-10 02:03:21,222 - INFO - Theoretical sync time (1 worker): ~0.54s
2026-05-10 02:03:21,223 - INFO - Theoretical async time (3 workers): ~0.18s
2026-05-10 02:03:21,412 - INFO - Actual async time: 0.19s
2026-05-10 02:03:21,412 - INFO - Speedup: 2.85x
```