# main.py
"""
Демонстрация работы AsyncTaskExecutor — Лабораторная работа №4.

Запускает сценарии обработки задач с хэндлерами из src/handlers.py:
PrintHandler, TransformHandler, StatusUpdateHandler, MetricsHandler.
"""
from __future__ import annotations

import asyncio
import logging
import time

from src.task import Task
from src.executor import AsyncTaskExecutor
from src.handlers import (
    PrintHandler,
    TransformHandler,
    StatusUpdateHandler,
    MetricsHandler,
)
from src.exceptions import TaskProcessingError, ExecutorError

# Настройка логирования (единый стиль с ЛР3)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ─── Вспомогательные функции ─────────────────────────────────────────────────────

def create_demo_tasks(count: int = 6, prefix: str = "demo") -> list[Task]:
    """Создать набор задач для демонстрации."""
    payloads = [
        "urgent: fix critical bug",
        "important: update docs",
        "normal: refactor module",
        "low: cleanup temp files",
        "archive: migrate data",
        "test with <script> tags",
    ]
    tasks = []
    for i in range(count):
        task = Task(
            payload=payloads[i % len(payloads)],
            priority=(i % 10) + 1,
        )
        # Для читаемости в логах переопределяем приватный атрибут
        object.__setattr__(task, '_id', f"{prefix}-{i:02d}")
        tasks.append(task)
    return tasks


# ─── Асинхронные демо-сценарии ──────────────────────────────────────────────────

async def demo_print_handler() -> None:
    """Сценарий 1: Базовое выполнение с PrintHandler."""
    logger.info("\n=== Scenario 1: PrintHandler ===")

    tasks = create_demo_tasks(5, prefix="print")
    start = time.perf_counter()

    async with AsyncTaskExecutor(workers=3) as executor:
        executor.register_handler(PrintHandler())

        for task in tasks:
            await executor.submit(task)
            logger.debug(f"Submitted: {task.id}")

        await executor.wait_all()

    elapsed = time.perf_counter() - start
    logger.info(f"Processed: {executor.processed_count} tasks")
    logger.info(f"Errors: {len(executor.errors)}")
    logger.info(f"Elapsed: {elapsed:.2f}s")


async def demo_transform_handler() -> None:
    """Сценарий 2: Преобразование payload с TransformHandler."""
    logger.info("\n=== Scenario 2: TransformHandler ===")

    tasks = create_demo_tasks(4, prefix="trans")

    async with AsyncTaskExecutor(workers=2) as executor:
        executor.register_handler(TransformHandler())

        for task in tasks:
            logger.debug(f"Before: {task.id} payload='{task.payload}'")
            await executor.submit(task)

        await executor.wait_all()

    logger.info("After transformation:")
    for task in tasks:
        logger.info(f"  {task.id}: '{task.payload}'")
    logger.info(f"Errors: {len(executor.errors)}")


async def demo_status_handler() -> None:
    """Сценарий 3: Обновление статусов с StatusUpdateHandler."""
    logger.info("\n=== Scenario 3: StatusUpdateHandler ===")

    tasks = create_demo_tasks(9, prefix="status")

    async with AsyncTaskExecutor(workers=3) as executor:
        executor.register_handler(StatusUpdateHandler())

        for task in tasks:
            await executor.submit(task)

        await executor.wait_all()

    # Подсчёт финальных статусов
    status_counts: dict[str, int] = {}
    for task in tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1

    logger.info("Final status distribution:")
    for status, count in sorted(status_counts.items()):
        logger.info(f"  • {status}: {count} tasks")
    logger.info(f"Errors: {len(executor.errors)}")


async def demo_metrics_handler() -> None:
    """Сценарий 4: Сбор метрик с MetricsHandler."""
    logger.info("\n=== Scenario 4: MetricsHandler ===")

    tasks = create_demo_tasks(4, prefix="metrics")

    async with AsyncTaskExecutor(workers=2) as executor:
        # Для сбора результатов обернём хэндлер
        class CollectingHandler:
            def __init__(self, base_handler: MetricsHandler):
                self.base = base_handler
                self.results: list[dict] = []

            async def handle(self, task: Task) -> dict:
                result = await self.base.handle(task)
                self.results.append(result)
                return result

        collector = CollectingHandler(MetricsHandler())
        executor.register_handler(collector)  # type: ignore

        for task in tasks:
            await executor.submit(task)

        await executor.wait_all()

        # Выводим собранные метрики
        logger.info("Collected metrics:")
        for m in collector.results:
            logger.info(
                f"  {m['task_id']}: age={m['age_seconds']}s, "
                f"complexity={m['complexity_score']} ({m['category']})"
            )

    logger.info(f"Processed: {executor.processed_count} tasks")
    logger.info(f"Errors: {len(executor.errors)}")


async def demo_error_handling() -> None:
    """Сценарий 5: Демонстрация обработки ошибок."""
    logger.info("\n=== Scenario 5: Error handling ===")

    # Хэндлер, который падает на высоком приоритете
    class FailingHandler:
        async def handle(self, task: Task) -> str:
            await asyncio.sleep(task.priority * 0.02)
            if task.priority >= 8:
                raise ValueError(f"Too high priority: {task.priority}")
            logger.info(f"✓ Processed: {task.id}")
            return f"ok:{task.id}"

    tasks = create_demo_tasks(8, prefix="error")

    async with AsyncTaskExecutor(workers=2) as executor:
        executor.register_handler(FailingHandler())  # type: ignore

        for task in tasks:
            await executor.submit(task)

        await executor.wait_all()

    logger.info(f"Successfully processed: {executor.processed_count}")
    logger.info(f"Errors caught: {len(executor.errors)}")

    if executor.errors:
        logger.warning("Error details:")
        for err in executor.errors:
            logger.warning(f"  • {err.task.id} (priority={err.task.priority}): {err.cause}")


async def demo_concurrency() -> None:
    """Сценарий 6: Демонстрация конкурентности."""
    logger.info("\n=== Scenario 6: Concurrency check ===")

    tasks = [Task(payload=f"conc-task-{i}", priority=3) for i in range(6)]
    sync_estimate = sum(3 * 0.03 for _ in tasks)  # priority * 0.03 из PrintHandler

    logger.info(f"Theoretical sync time (1 worker): ~{sync_estimate:.2f}s")
    logger.info(f"Theoretical async time (3 workers): ~{sync_estimate / 3:.2f}s")

    start = time.perf_counter()

    async with AsyncTaskExecutor(workers=3) as executor:
        executor.register_handler(PrintHandler())
        for task in tasks:
            await executor.submit(task)
        await executor.wait_all()

    elapsed = time.perf_counter() - start
    logger.info(f"Actual async time: {elapsed:.2f}s")
    logger.info(f"Speedup: {sync_estimate / elapsed:.2f}x")


# ─── Главный запуск ─────────────────────────────────────────────────────────────

async def _run_all_demos() -> None:
    """Запустить все асинхронные демо-сценарии."""
    logger.info("AsyncTaskExecutor demonstration started.")

    await demo_print_handler()
    await asyncio.sleep(0.1)

    await demo_transform_handler()
    await asyncio.sleep(0.1)

    await demo_status_handler()
    await asyncio.sleep(0.1)

    await demo_metrics_handler()
    await asyncio.sleep(0.1)

    await demo_error_handling()
    await asyncio.sleep(0.1)

    await demo_concurrency()

    logger.info("Demonstration completed successfully.")


def main() -> None:
    """Точка входа — синхронная обёртка для async-демо."""
    try:
        asyncio.run(_run_all_demos())

    except TaskProcessingError as e:
        logger.error(f"Task processing error: {e}")
        raise
    except ExecutorError as e:
        logger.error(f"Executor error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()