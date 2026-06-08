"""Обработчик для curl_tool."""

import json
from typing import Dict, Any

def handle_request_curl(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает запрос для curl_tool.
    
    Args:
        params: Параметры запроса
        
    Returns:
        Результат выполнения
    """
    return {
        "success": True,
        "message": "curl_tool выполнен",
        "params": params
    }

__all__ = ['handle_request_curl']
