"""
Base Agent implementation following the ReAct (Reasoning + Acting) pattern.
Handles multi-step reasoning, tool dispatching, execution tracing, and real-time event streaming.
"""

from typing import Dict, Any, List, Optional, Callable
import time
import logging
from taskflow.core.tool import ToolRegistry, Tool, default_registry
from taskflow.core.llm_provider import LLMProvider, LLMResponse

logger = logging.getLogger("taskflow.agent")

class AgentStep:
    def __init__(self, step_number: int, thought: str, action: Optional[str] = None, 
                 parameters: Optional[Dict[str, Any]] = None, observation: Optional[Any] = None):
        self.step_number = step_number
        self.thought = thought
        self.action = action
        self.parameters = parameters or {}
        self.observation = observation
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "parameters": self.parameters,
            "observation": self.observation,
            "timestamp": self.timestamp
        }


class AgentRunResult:
    def __init__(self, agent_name: str, task: str, final_answer: str, steps: List[AgentStep], success: bool = True):
        self.agent_name = agent_name
        self.task = task
        self.final_answer = final_answer
        self.steps = steps
        self.success = success
        self.duration_seconds = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "task": self.task,
            "final_answer": self.final_answer,
            "steps": [s.to_dict() for s in self.steps],
            "success": self.success,
            "duration_seconds": self.duration_seconds
        }


class BaseAgent:
    def __init__(
        self,
        name: str,
        role: str,
        system_instruction: str,
        tools: Optional[List[Tool]] = None,
        llm_provider: Optional[LLMProvider] = None,
        max_steps: int = 8
    ):
        self.name = name
        self.role = role
        self.system_instruction = system_instruction
        self.tool_registry = ToolRegistry()
        if tools:
            for t in tools:
                self.tool_registry.register(t)
        self.llm = llm_provider or LLMProvider()
        self.max_steps = max_steps
        self._listeners: List[Callable[[str, Dict[str, Any]], None]] = []

    def add_listener(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Subscribe to live agent events (thought, tool_call, tool_result, finish)."""
        self._listeners.append(callback)

    def _emit(self, event_type: str, data: Dict[str, Any]):
        for listener in self._listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.warning(f"Error in agent event listener: {e}")

    def run(self, task: str) -> AgentRunResult:
        """Execute task using ReAct reasoning & acting loop."""
        start_time = time.time()
        steps: List[AgentStep] = []
        self._emit("start", {"agent": self.name, "task": task})

        system_prompt = f"""You are {self.name}, an expert AI Agent specializing in: {self.role}.
Your objective is to automate repetitive tasks reliably and accurately.

Instructions:
- Decompose the task into logical steps.
- If you need information or need to modify files, call appropriate tools.
- Provide clear, concise executive explanations.

{self.system_instruction}
"""
        history_context = []
        final_answer = ""
        success = True

        for step_idx in range(1, self.max_steps + 1):
            prompt = f"Task: {task}\n\n"
            if steps:
                prompt += "Previous Steps and Observations:\n"
                for s in steps:
                    prompt += f"Step {s.step_number}:\nThought: {s.thought}\n"
                    if s.action:
                        prompt += f"Action: {s.action}({s.parameters})\nObservation: {s.observation}\n"
                prompt += "\nDecide your next action or provide the final answer if complete."

            # Query LLM
            response = self.llm.generate(
                prompt=prompt,
                system_instruction=system_prompt,
                tools=self.tool_registry.to_schemas()
            )

            thought = response.content
            tool_calls = response.tool_calls

            if not tool_calls:
                # Finished reasoning
                final_answer = thought
                step = AgentStep(step_number=step_idx, thought=thought)
                steps.append(step)
                self._emit("thought", {"step": step_idx, "thought": thought})
                break

            # Execute tool call
            first_call = tool_calls[0]
            action_name = first_call.get("name")
            action_params = first_call.get("parameters", {})

            self._emit("tool_call", {
                "step": step_idx,
                "tool": action_name,
                "parameters": action_params,
                "thought": thought
            })

            tool = self.tool_registry.get(action_name)
            if tool:
                observation = tool.execute(**action_params)
            else:
                observation = f"Error: Tool '{action_name}' not found."

            self._emit("tool_result", {
                "step": step_idx,
                "tool": action_name,
                "observation": observation
            })

            step = AgentStep(
                step_number=step_idx,
                thought=thought,
                action=action_name,
                parameters=action_params,
                observation=observation
            )
            steps.append(step)

        if not final_answer and steps:
            final_answer = steps[-1].thought or "Task processing completed."

        result = AgentRunResult(
            agent_name=self.name,
            task=task,
            final_answer=final_answer,
            steps=steps,
            success=success
        )
        result.duration_seconds = round(time.time() - start_time, 3)

        self._emit("finish", result.to_dict())
        return result
