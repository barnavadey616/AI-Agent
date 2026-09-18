"""
Tool system and registry for TaskFlow AI Agents.
Provides a clean decorator and registry for tools exposed to agents.
"""

from typing import Callable, Any, Dict, List, Optional
import inspect
import json
import logging

logger = logging.getLogger("taskflow.tool")

class Tool:
    def __init__(self, name: str, description: str, func: Callable, parameters: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or self._infer_parameters(func)

    def _infer_parameters(self, func: Callable) -> Dict[str, Any]:
        """Infer JSON schema parameters from Python type annotations and docstrings."""
        sig = inspect.signature(func)
        properties = {}
        required = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls"]:
                continue
            
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                param_type = type_map.get(param.annotation, "string")
                
            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter: {param_name}"
            }
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def execute(self, **kwargs) -> Any:
        """Safely execute the tool with given arguments."""
        try:
            return self.func(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool '{self.name}': {e}", exc_info=True)
            return {"error": str(e), "tool": self.name}

    def __call__(self, *args, **kwargs) -> Any:
        """Allow calling the tool directly as a standard Python function."""
        return self.func(*args, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def to_schemas(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tools.values()]


# Global default registry
default_registry = ToolRegistry()


def tool(name: Optional[str] = None, description: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None, registry: Optional[ToolRegistry] = None):
    """Decorator to convert a function into an Agent Tool."""
    def decorator(func: Callable) -> Tool:
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip() or f"Executes {tool_name}"
        t = Tool(name=tool_name, description=tool_desc, func=func, parameters=parameters)
        target_reg = registry or default_registry
        target_reg.register(t)
        return t
    return decorator
