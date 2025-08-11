# tools.py
from typing import Any

from src.llm_tools.base_tool import BasePromptTool
from src.llm_tools.executive_summary_tool import ExecutiveSummaryTool
from src.llm_tools.oneliner_tool import OneLinerTool

# Tool Map and Analysis Function
TOOL_MAP: dict[str, type[BasePromptTool[Any]]] = {
    OneLinerTool.tool_name: OneLinerTool,
    ExecutiveSummaryTool.tool_name: ExecutiveSummaryTool,
    # Add other tools here
}
