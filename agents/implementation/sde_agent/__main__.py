from common.server import A2AServer
from common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from task_manager import AgentTaskManager
from agent import SDEAgent
import click
import os
import logging
from starlette.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10004)
def main(host, port):
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="website_generation",
            name="Website Generation Tool",
            description="Allows website generation by user prompt.",
            tags=["sde", "website_generation", "code_generation", "software_development"],
            examples=[
                "Generate Python code for a web scraper.",
                "Can you debug my JavaScript application?",
            ],
        )

        agent_card = AgentCard(
            name="SDE Agent",
            description="This agent made by GitVerse helps with various software development tasks such as generating code, running tests, and refining solutions based on developer inputs.",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=SDEAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=SDEAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )
        server = A2AServer(
            agent_card=agent_card,
            task_manager=AgentTaskManager(agent=SDEAgent()),
            host=host,
            port=port,
        )

        # Add CORSMiddleware to allow requests from any origin (disables CORS restrictions)
        server.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins
            allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
            allow_headers=["*"],  # Allow all headers
        )

        server.start()
    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
