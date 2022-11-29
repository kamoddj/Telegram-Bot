class FormatError(Exception):
    """Ошибка, если формат response не json."""
    pass

class EmptyVariables(Exception):
    """Одна из переменных пустая или не правильная"""
    pass

class EndpointError(Exception):
    """Ошбика адреса."""
    pass

class DataTypeError(Exception):
    """Ошибка, если тип данных не dict."""
    pass

class HomeworkIsNone(Exception):
    """Обьект домашней работы не найден"""
    pass
