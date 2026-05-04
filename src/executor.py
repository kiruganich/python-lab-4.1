from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
import logging
import asyncio

from src.task import Task
from src.exceptions import ExecutorErrror, TaskProcessingError, ExecutorNotStartedError, HandlerNotFoundError
from src.handlers import TaskHandler

logger = logging.getLogger(__name__)


class AsyncTaskExecutor:
    def __init__(self, workers: int = 2, handler: TaskHandler | None = None):
        self._workers_count: int = workers
        self._handler: TaskHandler | None = handler
        self._queue: asyncio.Queue[Task | None] = None
        self._running = False
        self._errors: list[TaskProcessingError] = []
        self._processed_count = 0
        self._worker_tasks: list[asyncio.Task] = []