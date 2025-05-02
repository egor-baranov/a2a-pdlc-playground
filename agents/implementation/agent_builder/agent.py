import json
import random
from typing import Any, AsyncIterable, Dict, Optional
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Local cache of created request_ids for demo purposes.
task_ids = set()

# A set to track QA task IDs for demonstration purposes.
qa_task_ids = set()


def generate_tests(qa_details: dict[str, Any]) -> dict[str, Any]:
    """
    Generate test cases based on the provided QA details.

    Args:
        qa_details (dict[str, Any]): A dictionary containing details about the functionality or feature under test, such as:
            - 'feature': the feature or functionality under test.
            - 'test_requirements': a detailed description of what must be verified, including edge cases.
            - 'constraints': any specific testing constraints or requirements.

    Returns:
        dict[str, Any]: A dictionary containing the generated test cases, a unique qa_task_id, and the QA details.
    """
    qa_task_id = "qa_task_id_" + str(random.randint(1000000, 9999999))
    qa_task_ids.add(qa_task_id)
    qa_details['qa_task_id'] = qa_task_id

    # Placeholder generated test cases. Replace with actual test generation logic as needed.
    generated_tests = (
        f"# Auto-generated test cases for QA task {qa_task_id}\n"
        f"# Feature: {qa_details.get('feature', 'N/A')}\n"
        f"# Test Requirements: {qa_details.get('test_requirements', 'N/A')}\n"
        f"# Constraints: {qa_details.get('constraints', 'N/A')}\n\n"
        "def test_feature():\n"
        "    # TODO: Implement the actual test logic here\n"
        "    assert True\n"
    )
    return {
        "qa_task_id": qa_task_id,
        "tests": generated_tests,
        "qa_details": qa_details,
    }


def run_tests(qa_task_id: str, tests: str) -> dict[str, Any]:
    """
    Execute the generated test cases for a given QA task.

    Args:
        qa_task_id (str): The unique identifier for the QA task.
        tests (str): The generated test code that should be executed.

    Returns:
        dict[str, Any]: A dictionary containing the qa_task_id and the status/result of the test execution.
    """
    if qa_task_id not in qa_task_ids:
        return {"qa_task_id": qa_task_id, "status": "Error: Invalid qa_task_id."}

    # In a real scenario, dynamically execute the provided test cases.
    # For demonstration purposes, we simulate test execution.
    test_results = "All tests passed."  # This placeholder should be replaced with real test outcomes.

    return {
        "qa_task_id": qa_task_id,
        "status": test_results,
    }


def return_feedback(qa_details: dict[str, Any],
                    tests_info: dict[str, Any],
                    feedback_instructions: Optional[str] = None) -> dict[str, Any]:
    """
    Return a structured feedback report for the QA task after executing tests.

    Args:
        qa_details (dict[str, Any]): The original QA details provided for the task.
        tests_info (dict[str, Any]): A dictionary with the outcomes of the test execution.
        feedback_instructions (Optional[str]): Any additional instructions or context for the feedback.

    Returns:
        dict[str, Any]: A dictionary containing the qa_task_id, test outcomes, and a summary of the QA process including any additional feedback.
    """
    feedback_report = {
        "qa_task_id": qa_details.get("qa_task_id", ""),
        "feedback": (
            f"Test execution status: {tests_info.get('status', 'No status provided')}. "
            f"QA Details: {json.dumps(qa_details)}. "
            f"{'Additional feedback: ' + feedback_instructions if feedback_instructions else ''}"
        ),
    }
    return feedback_report


def run_tests(task_id: str, code: str) -> dict[str, Any]:
    """
    Execute tests for the generated code corresponding to the given task_id.

    Args:
        task_id (str): The unique identifier for the coding task.
        code (str): The generated code that needs to be validated via tests.

    Returns:
        dict[str, Any]: A dictionary containing the status and results of the test execution.
    """
    # Verify the task_id exists.
    if task_id not in task_ids:
        return {"task_id": task_id, "status": "Error: Invalid task_id."}

    # In a real-world scenario, you would dynamically run tests against the code.
    # Here, we simulate test execution.
    test_results = "All tests passed."  # Replace with real test outcomes as applicable.

    return {
        "task_id": task_id,
        "status": test_results,
    }


def return_solution(task_details: dict[str, Any], code_info: dict[str, Any], test_results: dict[str, Any]) -> dict[
    str, Any]:
    """
    Return a final structured JSON object that represents the completed SDE solution.

    Args:
        task_details (dict[str, Any]): The details of the coding task.
        code_info (dict[str, Any]): A dictionary containing the generated code and associated task_id.
        test_results (dict[str, Any]): The results from running tests on the generated code.

    Returns:
        dict[str, Any]: A JSON-friendly dictionary containing the task_id, generated code, testing status,
                        and summary of task details.
    """
    solution = {
        "task_id": code_info.get("task_id", ""),
        "code": code_info.get("code", ""),
        "test_status": test_results.get("status", ""),
        "task_details": task_details,
    }
    # Optionally, to return a JSON string, uncomment the next line:
    # return json.dumps(solution)
    return solution


class AgentBuilderTemplate:
    """An agent that handles reimbursement requests."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    _agent: LlmAgent

    def __init__(self, llm_agent: LlmAgent):
        self._agent = llm_agent
        self._user_id = "remote_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def invoke(self, query, session_id) -> str:
        session = self._runner.session_service.get_session(
            app_name=self._agent.name, user_id=self._user_id, session_id=session_id
        )
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        events = list(self._runner.run(
            user_id=self._user_id, session_id=session.id, new_message=content
        ))
        if not events or not events[-1].content or not events[-1].content.parts:
            return ""
        return "\n".join([p.text for p in events[-1].content.parts if p.text])

    async def stream(self, query, session_id) -> AsyncIterable[Dict[str, Any]]:
        session = self._runner.session_service.get_session(
            app_name=self._agent.name, user_id=self._user_id, session_id=session_id
        )
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
                user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if (
                        event.content
                        and event.content.parts
                        and event.content.parts[0].text
                ):
                    response = "\n".join([p.text for p in event.content.parts if p.text])
                elif (
                        event.content
                        and event.content.parts
                        and any([True for p in event.content.parts if p.function_response])):
                    response = next((p.function_response.model_dump() for p in event.content.parts))
                yield {
                    "is_task_complete": True,
                    "content": response,
                }
            else:
                yield {
                    "is_task_complete": False,
                    "updates": "Processing the QA request...",
                }
