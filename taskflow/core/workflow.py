"""
Workflow Pipeline Engine for chaining multi-agent and multi-tool automated jobs.
"""

from typing import List, Dict, Any, Callable
import time
import logging
from taskflow.core.agent import BaseAgent, AgentRunResult

logger = logging.getLogger("taskflow.workflow")

class WorkflowStep:
    def __init__(self, name: str, agent_or_fn: Any, description: str = ""):
        self.name = name
        self.agent_or_fn = agent_or_fn
        self.description = description

class Workflow:
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []

    def add_step(self, name: str, agent_or_fn: Any, description: str = "") -> "Workflow":
        self.steps.append(WorkflowStep(name=name, agent_or_fn=agent_or_fn, description=description))
        return self

    def execute(self, initial_input: Any = None) -> Dict[str, Any]:
        """Run workflow steps sequentially, passing context along."""
        logger.info(f"Starting workflow: {self.name} ({len(self.steps)} steps)")
        start_time = time.time()
        context = {"input": initial_input, "step_results": {}}

        for step in self.steps:
            logger.info(f"Executing workflow step: {step.name}")
            step_start = time.time()
            result = None

            try:
                if isinstance(step.agent_or_fn, BaseAgent):
                    prompt = str(context.get("input") or step.description)
                    agent_result: AgentRunResult = step.agent_or_fn.run(prompt)
                    result = agent_result.to_dict()
                elif callable(step.agent_or_fn):
                    result = step.agent_or_fn(context)
                else:
                    result = {"status": "skipped", "reason": "unknown step runner type"}
            except Exception as e:
                logger.error(f"Error in step '{step.name}': {e}", exc_info=True)
                result = {"error": str(e), "success": False}

            context["step_results"][step.name] = {
                "result": result,
                "duration": round(time.time() - step_start, 3)
            }
            # Update input for next step if relevant
            if isinstance(result, dict) and "final_answer" in result:
                context["last_output"] = result["final_answer"]

        context["workflow_name"] = self.name
        context["total_duration"] = round(time.time() - start_time, 3)
        return context
