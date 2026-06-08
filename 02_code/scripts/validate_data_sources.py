import json
import sys
from pathlib import Path

def validate_and_extract_json(root_path: str = r"E:\AGI") -> dict:
    """Валидация JSON-файлов и извлечение структуры данных (Python 3.6+ совместимость)."""
    results = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "validated_files": {},
        "schema_samples": {},
        "errors": [],
        "integration_candidates": []
    }
    
    json_files = [
        "социальные_данные.json",
        "trello_cleaned.json",
        "test.json"
    ]
    
    for fname in json_files:
        fpath = Path(root_path) / fname
        if not fpath.exists():
            results["errors"].append(f"{fname}: not found")
            continue
        
        size = fpath.stat().st_size
        if size == 0:
            results["errors"].append(f"{fname}: empty file (0 bytes)")
            continue
        
        try:
            # Попытка парсинга с fallback кодировками
            for encoding in ["utf-8-sig", "utf-8", "cp1251"]:
                try:
                    with open(fpath, "r", encoding=encoding) as f:
                        data = json.load(f)
                    break
                except UnicodeDecodeError:
                    if encoding == "cp1251":
                        raise
            else:
                raise UnicodeDecodeError("fallback failed", b"", 0, 0, "")
            
            # Анализ структуры
            schema = _infer_schema(data)
            record_count = _count_records(data)
            
            results["validated_files"][fname] = {
                "size_bytes": size,
                "record_count": record_count,
                "schema": schema,
                "valid_json": True,
                "encoding_used": encoding
            }
            
            if size > 100 and record_count > 0:
                results["integration_candidates"].append(fname)
                results["schema_samples"][fname] = _get_sample(data, max_items=2)
                
        except Exception as e:
            results["errors"].append(f"{fname}: {type(e).__name__}: {str(e)[:120]}")
    
    return results

def _infer_schema(obj: any, max_depth: int = 3) -> dict:
    if max_depth <= 0:
        return {"type": type(obj).__name__}
    
    if isinstance(obj, dict):
        fields = {}
        for k, v in list(obj.items())[:8]:
            fields[str(k)] = _infer_schema(v, max_depth - 1)
        return {"type": "object", "field_count": len(obj), "sample_fields": fields}
    
    elif isinstance(obj, list):
        if not obj:
            return {"type": "array", "length": 0}
        return {
            "type": "array",
            "length": len(obj),
            "item_type": _infer_schema(obj[0], max_depth - 1) if obj else "unknown"
        }
    
    else:
        return {"type": type(obj).__name__}

def _count_records(obj: any) -> int:
    if isinstance(obj, list):
        return len(obj)
    elif isinstance(obj, dict):
        lists = [v for v in obj.values() if isinstance(v, list)]
        return max((len(v) for v in lists), default=1)
    return 1

def _get_sample(obj: any, max_items: int = 2) -> any:
    if isinstance(obj, list):
        return obj[:max_items]
    elif isinstance(obj, dict):
        return {k: (v[:max_items] if isinstance(v, list) else v) 
                for k, v in list(obj.items())[:max_items]}
    return obj

if __name__ == "__main__":
    result = validate_and_extract_json()
    
    # Кросс-версионный вывод в UTF-8
    if sys.version_info >= (3, 7):
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Fallback для Python < 3.7
        import io
        output = json.dumps(result, indent=2, ensure_ascii=False)
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        print(output)