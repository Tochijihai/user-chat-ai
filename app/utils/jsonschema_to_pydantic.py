from typing import Dict, Any, Type
from pydantic import BaseModel, create_model

_type_map = {
    "string": (str, ...),
    "integer": (int, ...),
    "number": (float, ...),
    "boolean": (bool, ...),
}

def model_from_json_schema(name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    * 単純な 'type': 'object' & プリミティブ型のみ対応
    * required 以外は Optional 扱い
    """
    if schema.get("type") != "object":
        raise ValueError("root schema must have type=object")
    fields = {}
    required = set(schema.get("required", []))
    for prop_name, prop in schema.get("properties", {}).items():
        ptype, default = _type_map.get(prop.get("type"), (str, ...))
        if prop_name not in required:
            default = None  # Optional
        fields[prop_name] = (ptype, default)
    return create_model(name, **fields)  # type: ignore
