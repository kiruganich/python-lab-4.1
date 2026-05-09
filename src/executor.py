from __future__ import annotations
from typing import Any
import logging
import asyncio

from src.task import Task
from src.exceptions import TaskProcessingError, ExecutorNotStartedError, HandlerNotFoundError, InvalidHandlerError
from src.handlers import TaskHandler

logger = logging.getLogger(__name__)


class AsyncTaskExecutor:

    SHUTDOWN_TIMEOUT: float = 5.0

    def __init__(self, workers: int = 2, handler: TaskHandler | None = None):
        if workers < 1:
            raise ValueError("workers must be at least 1")
        self._workers_count: int = workers
        self._handler: TaskHandler | None = handler
        self._queue: asyncio.Queue[Task | None] = None
        self._running = False
        self._errors: list[TaskProcessingError] = []
        self._processed_count = 0
        self._worker_tasks: list[asyncio.Task] = []



    def register_handler(self, handler: object) -> None:
        if not isinstance(handler, TaskHandler):
            logger.error(
                f"Handler registration failed: {type(handler).__name__} "
                f"does not implement TaskHandler protocol"
            )
            raise InvalidHandlerError(
                f"Handler must implement TaskHandler protocol with async def handle(task: Task). "
                f"Got: {type(handler).__name__}"
            )
        self._handler = handler
        logger.info(f"Handler registered: {type(handler).__name__}")

    async def submit(self, task: Task) -> None:
        if not self._running or self._queue is None:
            logger.error("Attempt to submit task while executor is not running")
            raise ExecutorNotStartedError(
                "Executor is not running. Use 'async with AsyncTaskExecutor(...)' context."
            )
        await self._queue.put(task)
        logger.debug(f"Task submitted: {task.id[:8]}... priority={task.priority}")

    async def wait_all(self) -> None:
        if self._queue is not None:
            logger.info("Waiting for all tasks to be processed...")
            await self._queue.join()
            logger.info("All tasks processed")

    async def _worker_loop(self, name: str) -> None:
        logger.debug(f"[{name}] Worker started")
        while True:
            task = await self._queue.get()

            if task is None:
                logger.debug(f"[{name}] Received sentinel, shutting down")
                self._queue.task_done()
                break

            try:
                if self._handler is None:
                    logger.error("Handler Not Found Error: No handler registered")
                    raise HandlerNotFoundError("No handler registered")


                logger.debug(f"[{name}] Processing task: {task.id[:8]}...")
                await self._handler.handle(task)

                self._processed_count += 1
                logger.info(f"[{name}] Task completed: {task.id[:8]}...")

            except Exception as e:
                error = TaskProcessingError(task, e)
                self._errors.append(error)
                logger.error(
                    f"[{name}] Task processing error: {task.id[:8]}... | "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )

            finally:
                self._queue.task_done()

        logger.debug(f"[{name}] Worker stopped")

    async def __aenter__(self) -> AsyncTaskExecutor:
        logger.info(f"Starting executor with {self._workers_count} workers")
        self._queue = asyncio.Queue()
        self._running = True
        self._errors = []
        self._processed_count = 0

        self._worker_tasks = [
            asyncio.create_task(self._worker_loop(f"worker-{i}"))
            for i in range(self._workers_count)
        ]
        logger.debug(f"Created {len(self._worker_tasks)} worker tasks")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        """Остановить исполнитель и дождаться завершения воркеров."""
        logger.info("Stopping executor...")

        # Отправляем сигналы остановки
        if self._queue is not None:
            for _ in range(self._workers_count):
                await self._queue.put(None)
            logger.debug(f"Sent {self._workers_count} sentinels")

        # Ждём завершения с таймаутом
        if self._worker_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._worker_tasks, return_exceptions=True),
                    timeout=self.SHUTDOWN_TIMEOUT
                )
                logger.debug("All workers finished gracefully")
            except asyncio.TimeoutError:
                logger.warning(
                    f"Workers did not finish in {self.SHUTDOWN_TIMEOUT}s, cancelling..."
                )
                for task in self._worker_tasks:
                    task.cancel()
                # Ждём отмены
                await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        self._running = False
        self._worker_tasks = []
        self._queue = None

        logger.info("Executor stopped")
        return False


    @property
    def errors(self) -> list[TaskProcessingError]:
        return list(self._errors)

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def is_running(self) -> bool:
        return self._running