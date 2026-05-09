from __future__ import annotations
import asyncio
import time
import pytest
from typing import Any
from src.task import Task
from src.executor import AsyncTaskExecutor
from src.handlers import (
    TaskHandler,
    PrintHandler,
    TransformHandler,
    StatusUpdateHandler,
    MetricsHandler,
)
from src.exceptions import ExecutorNotStartedError, InvalidHandlerError

class FailingHandler:
    async def handle(self, task: Task) -> str:
        await asyncio.sleep(0.01)
        if task.priority > 5:
            raise ValueError(f"Priority too high: {task.priority}")
        return f"processed_{task.id}"

class TestHandlerProtocol:
    def test_register_print_handler(self):
        executor = AsyncTaskExecutor()
        handler = PrintHandler()
        executor.register_handler(handler)
        assert executor._handler is handler

    def test_register_transform_handler(self):
        executor = AsyncTaskExecutor()
        executor.register_handler(TransformHandler())
        assert isinstance(executor._handler, TransformHandler)

    def test_register_invalid_type_raises(self):
        executor = AsyncTaskExecutor()
        with pytest.raises(InvalidHandlerError, match="must implement TaskHandler protocol"):
            executor.register_handler("not a handler")

class TestExecutorLifecycle:
    @pytest.mark.asyncio
    async def test_context_manager_starts_executor(self):
        async with AsyncTaskExecutor(workers=2) as ex:
            assert ex.is_running is True
            assert ex._queue is not None
            assert len(ex._worker_tasks) == 2

    @pytest.mark.asyncio
    async def test_context_manager_stops_executor(self):
        ex = AsyncTaskExecutor(workers=2)
        async with ex:
            pass
        assert ex.is_running is False
        assert ex._queue is None

    @pytest.mark.asyncio
    async def test_submit_before_start_raises(self):
        ex = AsyncTaskExecutor()
        with pytest.raises(ExecutorNotStartedError):
            await ex.submit(Task(payload="test", priority=5))

class TestPrintHandler:
    @pytest.mark.asyncio
    async def test_basic_processing(self):
        tasks = [Task(payload=f"Payload {i}", priority=(i % 10) + 1) for i in range(5)]
        async with AsyncTaskExecutor(workers=2) as ex:
            ex.register_handler(PrintHandler())
            for t in tasks:
                await ex.submit(t)
            await ex.wait_all()
        assert ex.processed_count == 5
        assert len(ex.errors) == 0

    @pytest.mark.asyncio
    async def test_handler_return_value_ignored(self):
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(PrintHandler())
            await ex.submit(Task(payload="t1", priority=3))
            await ex.wait_all()
        assert ex.processed_count == 1

class TestTransformHandler:
    @pytest.mark.asyncio
    async def test_payload_uppercased(self):
        task = Task(payload="hello world", priority=2)
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(TransformHandler())
            await ex.submit(task)
            await ex.wait_all()
        assert task.payload == "HELLO WORLD"

    @pytest.mark.asyncio
    async def test_multiple_tasks_transformed(self):
        tasks = [
            Task(payload="alpha", priority=1),
            Task(payload="beta", priority=2),
            Task(payload="gamma", priority=3),
        ]
        async with AsyncTaskExecutor(workers=2) as ex:
            ex.register_handler(TransformHandler())
            for t in tasks:
                await ex.submit(t)
            await ex.wait_all()
        assert all(t.payload.isupper() for t in tasks)

class TestStatusUpdateHandler:
    @pytest.mark.asyncio
    async def test_high_priority_to_processing(self):
        task = Task(payload="urgent", priority=2)
        assert task.status == "new"
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(StatusUpdateHandler())
            await ex.submit(task)
            await ex.wait_all()
        assert task.status == "processing"

    @pytest.mark.asyncio
    async def test_medium_priority_to_ready(self):
        task = Task(payload="normal", priority=5)
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(StatusUpdateHandler())
            await ex.submit(task)
            await ex.wait_all()
        assert task.status == "ready"

    @pytest.mark.asyncio
    async def test_low_priority_cancelled(self):
        task = Task(payload="low", priority=9)
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(StatusUpdateHandler())
            await ex.submit(task)
            await ex.wait_all()
        assert task.status == "cancelled"

class TestMetricsHandler:
    @pytest.mark.asyncio
    async def test_returns_dict_with_keys(self):
        task = Task(payload="test payload", priority=4)
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(MetricsHandler())
            await ex.submit(task)
            await ex.wait_all()
        assert ex.processed_count == 1

    @pytest.mark.asyncio
    async def test_metrics_fields_present(self):
        task = Task(payload="test", priority=3)
        handler = MetricsHandler()
        result = await handler.handle(task)
        assert "task_id" in result
        assert "age_seconds" in result
        assert "processing_time" in result
        assert "complexity_score" in result
        assert "category" in result
        assert "payload_length" in result
        assert result["category"] in {"easy", "medium", "hard"}

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_handler_exception_caught(self):
        tasks = [
            Task(payload="ok", priority=2),
            Task(payload="fail", priority=8),
        ]
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(FailingHandler())
            for t in tasks:
                await ex.submit(t)
            await ex.wait_all()
        assert ex.processed_count == 1
        assert len(ex.errors) == 1
        assert "Priority too high" in str(ex.errors[0].cause)

    @pytest.mark.asyncio
    async def test_executor_continues_after_error(self):
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(FailingHandler())
            for i in range(5):
                await ex.submit(Task(payload=f"task-{i}", priority=(i + 1) * 2))
            await ex.wait_all()
        assert ex.processed_count == 2
        assert len(ex.errors) == 3

class TestConcurrency:
    @pytest.mark.asyncio
    async def test_multiple_workers_faster_than_single(self):
        tasks1 = [Task(payload=f"Task {i}", priority=3) for i in range(6)]
        start1 = time.perf_counter()
        async with AsyncTaskExecutor(workers=1) as ex1:
            ex1.register_handler(PrintHandler())
            for t in tasks1:
                await ex1.submit(t)
            await ex1.wait_all()
        time1 = time.perf_counter() - start1
        tasks2 = [Task(payload=f"Task {i}", priority=3) for i in range(6)]
        start3 = time.perf_counter()
        async with AsyncTaskExecutor(workers=3) as ex3:
            ex3.register_handler(PrintHandler())
            for t in tasks2:
                await ex3.submit(t)
            await ex3.wait_all()
        time3 = time.perf_counter() - start3
        assert time3 < time1 * 0.8

class TestExecutorProperties:
    @pytest.mark.asyncio
    async def test_errors_returns_copy(self):
        async with AsyncTaskExecutor(workers=1) as ex:
            ex.register_handler(FailingHandler())
            await ex.submit(Task(payload="fail", priority=9))
            await ex.wait_all()
        errors1 = ex.errors
        errors2 = ex.errors
        assert errors1 is not errors2

    @pytest.mark.asyncio
    async def test_processed_count_accuracy(self):
        async with AsyncTaskExecutor(workers=2) as ex:
            ex.register_handler(PrintHandler())
            for i in range(10):
                await ex.submit(Task(payload=f"task-{i}", priority=1))
            await ex.wait_all()
        assert ex.processed_count == 10
        assert len(ex.errors) == 0