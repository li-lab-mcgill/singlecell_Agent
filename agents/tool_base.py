from __future__ import annotations

from typing import Any, Callable, Dict, List


class AgentTool:
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    def run(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    def to_spec(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class AgentToolRegistry:
    def __init__(self) -> None:
        self.tools: Dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> "AgentToolRegistry":
        if not tool.name:
            raise ValueError("Tool name must be non-empty")
        if tool.name in self.tools:
            raise ValueError(f"Duplicate tool registration: {tool.name}")
        self.tools[tool.name] = tool
        return self

    def tool_specs(self) -> List[Dict[str, Any]]:
        return [tool.to_spec() for tool in self.tools.values()]

    def executor(self) -> Dict[str, Callable[..., Any]]:
        return {name: tool.run for name, tool in self.tools.items()}


class MultiToolBase:
    toolkit_name: str = ""
    brief_description: str = ""
    detailed_description: str = ""

    def get_doc(self) -> str:
        if self.detailed_description:
            return self.detailed_description
        return self.__doc__ or ""

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        raise NotImplementedError
