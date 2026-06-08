"""Обработчик для safe_list_directory_tool."""

import json
from typing import Dict, Any

def handle_request_safe_list_directory(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает запрос для safe_list_directory_tool.
    
    Args:
        params: Параметры запроса
        
    Returns:
        Результат выполнения
    """
    return {
        "success": True,
        "message": "safe_list_directory_tool выполнен",
        "params": params
    }

__all__ = ['handle_request_safe_list_directory']
