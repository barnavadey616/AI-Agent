"""
Unit tests for TaskFlow AI core components: Tool, ToolRegistry, BaseAgent, Workflow.
"""

import pytest
from taskflow.core.tool import Tool, ToolRegistry, tool
from taskflow.core.agent import BaseAgent
from taskflow.core.workflow import Workflow

def test_tool_decorator_and_parameters():
    @tool(name="sample_add", description="Adds two numbers")
    def sample_add(a: int, b: int) -> int:
        return a + b

    assert sample_add.name == "sample_add"
    assert sample_add.description == "Adds two numbers"
    
    # Execution
    res = sample_add.execute(a=5, b=10)
    assert res == 15

    # Schema
    schema = sample_add.to_dict()
    assert "properties" in schema["parameters"]
    assert "a" in schema["parameters"]["properties"]
    assert "b" in schema["parameters"]["properties"]

def test_tool_registry():
    reg = ToolRegistry()
    
    @tool(name="test_tool", registry=reg)
    def test_tool(x: str) -> str:
        return f"hello {x}"

    assert reg.get("test_tool") is not None
    assert len(reg.list_tools()) == 1
    assert reg.get("nonexistent") is None

def test_base_agent_execution():
    agent = BaseAgent(
        name="TestAgent",
        role="Tester",
        system_instruction="You are a test agent."
    )
    result = agent.run("Perform a quick test task")
    assert result.success is True
    assert result.agent_name == "TestAgent"
    assert len(result.steps) > 0

def test_workflow_execution():
    wf = Workflow(name="TestPipeline")
    wf.add_step("step1", lambda ctx: {"data": "step1_output"})
    wf.add_step("step2", lambda ctx: {"data": "step2_output"})

    res = wf.execute(initial_input="start")
    assert "step_results" in res
    assert "step1" in res["step_results"]
    assert "step2" in res["step_results"]
    assert res["workflow_name"] == "TestPipeline"
