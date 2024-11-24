import os
from typing import List
from instructor import from_openai
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


def format_for_llm(system_prompt: str, text: str) -> List[ChatCompletionMessageParam]:
    """
    Formats the messages into a set of messages for LLM.
    """
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]


ai_client = from_openai(OpenAI(api_key=os.environ["OPEN_AI_KEY"]))
