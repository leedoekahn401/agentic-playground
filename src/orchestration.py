from typing import Annotated, List
import operator

from env_config import config

from langchain.tools import tool
from langchain.chat_models import init_chat_model


llm = init_chat_model(
    "deepseek-chat",
    model_provider="openai",
    api_key=config.deepseek_api_key,
    base_url="https://api.deepseek.com",
    temperature=0
)

# Schema for structured output to use in planning
class Section(BaseModel):
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
    )


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the report.",
    )


# Augment the LLM with schema for structured output
planner = llm.with_structured_output(Sections)