from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
import logging
import asyncio

from src.task import Task
from src.exceptions import TaskIDError

logger = logging.getLogger(__name__)


@runtime_checkable
class TaskHandler(Protocol):

    def handle(self, task: Task) -> Any:
        """Метод обработки задачи"""
        ...



class PrintHandler(TaskHandler):
    async def handle(self, task: Task) -> str:
        await asyncio.sleep(task.priority * 0.03)
        logger.info(f"Print Handler got task - {task.id}: {task.payload}")
        return f"processed: {task.id}"
    

class TransformHandler(TaskHandler):
    """payload в верхний регистр"""
    
    async def handle(self, task: Task) -> str:
        await asyncio.sleep(task.priority * 0.03)
        
        original_payload = task.payload
        transformed = original_payload.upper()

        task.payload = transformed
        
        logger.info(
            f"TransformHandler: {task.id} | "
            f"'{original_payload}' -> '{transformed}'"
        )
        return f"transformed: {task.id}"
    


class StatusUpdateHandler(TaskHandler):
    """обновление статуса задачи"""
    
    async def handle(self, task: Task) -> str:
        await asyncio.sleep(task.priority * 0.02)
        
        old_status = task.status
        
        if task.priority <= 3:
            if task.status == "new":
                task._mark_processing()
        elif task.priority <= 7:
            if task.status == "new":
                task._mark_ready()
        else:
            if task.status == "new" and task.priority >= 9:
                task._mark_cancelled()
        
        new_status = task.status
        
        logger.info(
            f"StatusUpdateHandler: {task.id} | "
            f"status {old_status} -> {new_status} (priority={task.priority})"
        )
        return f"status updated: {task.id} ({old_status} -> {new_status})"


class MetricsHandler(TaskHandler):
    """сбор метрик о задаче"""
    
    async def handle(self, task: Task) -> dict[str, Any]:
        start_time = asyncio.get_event_loop().time()
        await asyncio.sleep(0.02)
        processing_time = asyncio.get_event_loop().time() - start_time
        
        complexity_score = (
            len(task.payload) * 0.1 + 
            task.priority * 2 + 
            task.age * 0.01
        )
        
        if complexity_score < 10:
            category = "easy"
        elif complexity_score < 30:
            category = "medium"
        else:
            category = "hard"
        
        metrics = {
            "task_id": task.id,
            "age_seconds": round(task.age, 2),
            "processing_time": round(processing_time, 4),
            "complexity_score": round(complexity_score, 2),
            "category": category,
            "payload_length": len(task.payload)
        }
        
        logger.info(
            f"MetricsHandler: {task.id} | "
            f"age={metrics['age_seconds']}s, "
            f"complexity={metrics['complexity_score']} ({category})"
        )
        return metrics