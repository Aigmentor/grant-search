import logging
import os
from typing import List
from instructor import from_openai
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import threading

logging.getLogger("httpx").setLevel(logging.WARNING)


def format_for_llm(system_prompt: str, text: str) -> List[ChatCompletionMessageParam]:
    """
    Formats the messages into a set of messages for LLM.
    """
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]


_ai_client = None
_lock = threading.Lock()


def get_ai_client():
    global _ai_client
    with _lock:
        if _ai_client is None:
            _ai_client = from_openai(
                OpenAI(api_key=os.environ["OPEN_AI_KEY"], timeout=12.0)
            )
            logging.info(f"AI client created")
    return _ai_client
