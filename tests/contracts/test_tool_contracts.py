# Tool Contract and Schema Verification Tests
import pytest
from tools.base import BaseTool, ToolPermission, ToolExecutionStatus, ToolResult
from tools.registry import create_default_investigation_tools

def test_all_investigation_tools_satisfy_read_only_contract():
    reg = create_default_investigation_tools()
    tools = reg.list_tools()
    
    assert len(tools) == 8
    for tool in tools:
        assert isinstance(tool, BaseTool)
        assert tool.name != ""
        assert tool.description != ""
        assert tool.permission_level == ToolPermission.READ_ONLY
        assert tool.timeout_seconds > 0
        assert tool.cost_estimate > 0

def test_tool_result_schema():
    res = ToolResult(
        tool_name="test_tool",
        status=ToolExecutionStatus.SUCCESS,
        duration_ms=12.4
    )
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.duration_ms == 12.4
    assert isinstance(res.evidence, list)
