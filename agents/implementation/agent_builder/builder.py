from common.server import A2AServer
from common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from task_manager import AgentTaskManager
from agent import AgentBuilderTemplate
import click
import os
import logging
from starlette.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentBuilder:
    _server: A2AServer
    _agent_card: AgentCard

    _host: int
    _port: int

    _llm_agent: LlmAgent
    _skills: list[AgentSkill]

    def __init__(self, host: int, port: int):
        try:
            if not os.getenv("GOOGLE_API_KEY"):
                raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

            self._host = host
            self._port = port
        except MissingAPIKeyError as e:
            logger.error(f"Error: {e}")
            exit(1)
        except Exception as e:
            logger.error(f"An error occurred during server startup: {e}")
            exit(1)

    def set_llm_agent(self, llm_agent: LlmAgent):
        self._llm_agent = llm_agent

    def set_skills(self, skills: list[AgentSkill]):
        self._skills = skills

    def build(self, name: str, description: str) -> A2AServer:
        try:
            capabilities = AgentCapabilities(streaming=True)
            self._agent_card = AgentCard(
                name=name,
                description=description,
                url=f"http://{self._host}:{self._port}/",
                version="1.0.0",
                defaultInputModes=AgentBuilderTemplate.SUPPORTED_CONTENT_TYPES,
                defaultOutputModes=AgentBuilderTemplate.SUPPORTED_CONTENT_TYPES,
                capabilities=capabilities,
                skills=self._skills,
            )

            self._server = A2AServer(
                agent_card=self._agent_card,
                task_manager=AgentTaskManager(
                    agent=AgentBuilderTemplate(
                        llm_agent=self._llm_agent
                    )
                ),
                host=self._host,
                port=self._port,
            )

            # Add CORSMiddleware to allow requests from any origin (disables CORS restrictions)
            self._server.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Allow all origins
                allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
                allow_headers=["*"],  # Allow all headers
            )
            return self._server
        except Exception as e:
            logger.error(f"An error occurred during server startup: {e}")
            exit(1)


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10005)
def main(host, port):
    builder = AgentBuilder(host, port)

    llm_agent = LlmAgent(
        model="gemini-2.0-flash-001",
        name="qa_agent",
        description=(
            "This agent assists with quality assurance tasks, including test case generation, test execution, "
            "and delivering actionable feedback on software functionality and performance."
        ),
        instruction="""
          You are an agent who assists with Quality Assurance (QA) for software developed within GitVerse.

          When you receive a QA request, you should first gather all necessary information:
            1. The functionality or feature that needs testing.
            2. Detailed descriptions of user flows, critical code sections, or functional requirements.
            3. Potential edge cases or error scenarios that should be verified.

          If any required information is missing, ask for clarification to ensure complete test coverage.

          Once you have all the necessary details, you should:
            - Generate a draft test plan or set of test cases using the generate_tests() tool.
            - Execute tests against the target functionality by calling run_tests().
            - Provide feedback and recommendations by calling return_feedback() with the test results and observations.

          In your response, include a summary of the QA process, the outcomes from the tests, and any identified issues or improvement suggestions.
              """,
        tools=[],
    )

    builder.set_llm_agent(llm_agent=llm_agent)
    builder.set_skills(skills=[
        AgentSkill(
            id="qa_assistance",
            name="QA Assistant Tool",
            description=(
                "Assists with quality assurance tasks including generating test cases, "
                "executing tests, and providing actionable feedback on software functionalities."
            ),
            tags=["qa", "quality_assurance", "testing", "feedback"],
            examples=[
                "Generate test cases for my login functionality.",
                "Run tests on the checkout process and provide feedback.",
            ],
        )
    ])

    server = builder.build(
        name="QA Agent",
        description=(
            "This agent made by GitVerse helps with quality assurance tasks. "
            "It generates test cases, runs tests, and delivers feedback for software features."
        )
    )
    server.start()


if __name__ == "__main__":
    main()
