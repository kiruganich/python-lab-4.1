"""
Исключения для модели задачи.

"""


class TaskValidationError(Exception):
    """
    Базовое исключение для ошибок валидации задачи.

    """
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
    """
    Базовое исключение для ошибок валидации источников

    """
    pass


class ExecutorErrror(Exception):
    """
    Базовое исключение исполнителя

    """
    pass


class TaskProcessingError(ExecutorErrror):
    """
    Ошибка обработки задач

    """
    pass


class ExecutorNotStartedError(ExecutorErrror):
    """
    Исполнитель не запущен
    
    """
    pass


class HandlerNotFoundError(ExecutorErrror):
    """
    Обработчик не найден
    
    """
    pass
