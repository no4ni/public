import pathlib
from typing import Dict, Any

def verify_file(path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
    p = pathlib.Path(path)
    if not p.exists():
        return {"exists": False, "error": "File not found", "path": str(p)}
    if p.is_dir():
        return {"exists": False, "error": "Is a directory", "path": str(p)}
    
    try:
        content = p.read_text(encoding=encoding)
    except (UnicodeDecodeError, PermissionError) as e:
        return {"exists": True, "error": f"Read failed: {type(e).__name__}", "path": str(p)}
    
    # Точное разделение с сохранением длины строк как в файле
    lines = content.split('\n')
    if content.endswith('\n'):
        lines.pop()  # Удалить пустую строку от завершающего \n
    
    return {
        "exists": True,
        "path": str(p.resolve()),
        "size_bytes": p.stat().st_size,
        "encoding_used": encoding,
        "lines_count": len(lines),
        "chars_total": len(content),
        "chars_per_line": [len(line) for line in lines],
        "chars_sum_lines": sum(len(line) for line in lines),
        "newlines_count": content.count('\n'),
        "mtime": p.stat().st_mtime
    }