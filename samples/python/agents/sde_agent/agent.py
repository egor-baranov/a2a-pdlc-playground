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
request_ids = set()

# A set to track task_ids for demonstration purposes.
task_ids = set()


def generate_code(task_details: dict[str, Any]) -> dict[str, Any]:
    """
    Generate code based on the provided task details.

    Args:
        task_details (dict[str, Any]): A dictionary containing details about the coding task such as:
            - 'language': the programming language to use.
            - 'requirements': a detailed description of the desired functionality,
            - 'constraints': any additional constraints or specifications.

    Returns:
        dict[str, Any]: A dictionary containing the generated code, a unique task_id, and the task details.
    """
    task_id = "task_id_" + str(random.randint(1000000, 9999999))
    task_ids.add(task_id)
    task_details['task_id'] = task_id

    # The generated code is a placeholder and should be replaced by actual code generation logic.
    generated_code = (
        f"# Auto-generated code for task {task_id}\n"
        f"# Language: {task_details.get('language', 'N/A')}\n"
        f"# Requirements: {task_details.get('requirements', 'N/A')}\n"
        f"# Constraints: {task_details.get('constraints', 'N/A')}\n\n"
        "def solution_function():\n"
        "    # TODO: Implement the solution here\n"
        "    pass\n"
    )
    return {
        "task_id": task_id,
        "code": generated_code,
        "task_details": task_details,
    }


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


class SDEAgent:
  """An agent that handles reimbursement requests."""

  SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

  def __init__(self):
    self._agent = self._build_agent()
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
    events = self._runner.run(
        user_id=self._user_id, session_id=session.id, new_message=content
    )
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
            "updates": "Processing the SDE request...",
        }

  def _build_agent(self) -> LlmAgent:
      """Builds the LLM agent for the Software Development Engineer (SDE) tasks."""
      return LlmAgent(
          model="gemini-2.0-flash-001",
          name="sde_agent",
          description=(
              "This agent assists with various software development tasks, including code generation, debugging, "
              "and solution validation."
          ),
          instruction="""
      You are an agent who assists the Software Development Engineer (SDE) with development tasks made by GitVerse.

      When you receive a software development request, you should first gather all necessary information:
        1. The programming language and frameworks involved.
        2. A detailed description of the task, such as feature implementation, bug fixes, or code refactoring.
        3. Any specific requirements, constraints, or deadlines.

      If the task request is incomplete, ask for any missing details to ensure clarity.

      Once you have all the required information, you should:
        - Generate a draft solution using the generate_code() tool.
        - Validate the solution by executing tests with run_tests().
        - Finalize your response by calling return_solution() with the task details and testing outcome.

      In your response, include a summary of the task details and the final status, indicating any improvements or modifications you applied.
          """,
          tools=[
              generate_code,
              run_tests,
              return_solution,
          ],
      )


