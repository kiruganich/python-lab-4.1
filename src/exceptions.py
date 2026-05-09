from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.task import Task


class TaskValidationError(Exception):
    """Базовое исключение для ошибок валидации задачи."""
    pass


class TaskIDError(TaskValidationError):
    """Ошибка валидации идентификатора задачи."""
    pass


class TaskPayloadError(TaskValidationError):
    """Ошибка валидации описания задачи."""
    pass


class TaskPriorityError(TaskValidationError):
    """Ошибка валидации приоритета задачи."""
    pass


class TaskStatusError(TaskValidationError):
    """Ошибка валидации статуса задачи."""
    pass


class TaskSourceValidationError(Exception):
    """Базовое исключение для ошибок валидации источников."""
    pass


class ExecutorError(Exception):
    """Базовое исключение исполнителя."""
    pass


class TaskProcessingError(ExecutorError):
    """
    Ошибка обработки задачи.
    
    Attributes:
        task: Задача, при обработке которой возникла ошибка
        cause: Исходное исключение
    """
    
    def __init__(self, task: "Task", cause: BaseException) -> None:
        self.task = task
        self.cause = cause
        super().__init__(
            f"Failed to process task {task.id}: {type(cause).__name__}: {cause}"
        )
    
    def __repr__(self) -> str:
        return f"TaskProcessingError(task_id={self.task.id!r}, cause={self.cause!r})"


class ExecutorNotStartedError(ExecutorError):
    """Исполнитель не запущен."""
    pass


class HandlerNotFoundError(ExecutorError):
    """Обработчик не найден."""
    pass

class InvalidHandlerError(ExecutorError):
    """Объект не реализует протокол TaskHandler."""
    pass