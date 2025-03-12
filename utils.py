from global_utils import get_logger
import io
import os
import json
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

logger = get_logger(__name__)

# Load environment variables
def load_env(env_path):
    """Load environment variables from .env file"""
    from dotenv import load_dotenv
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded environment from {env_path}")
    else:
        logger.warning(f"Environment file {env_path} not found")


async def call_llm(system_prompt, messages, model=None, tools=None):
    # Use model from environment variable if not explicitly provided
    async_llm = AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    if model is None:
        model = os.environ.get("LLM_MODEL")
    
    print(f"(Using anthropic {model})")
    
    # Create the request parameters
    params = {
        "model": model,
        "system": system_prompt,
        "max_tokens": 2000,
        "messages": messages,
        "temperature": 0,
    }
    
    # Add tools if provided
    if tools:
        params["tools"] = tools
    
    # Call the Anthropic API
    response = await async_llm.messages.create(**params)
    
    # Return the response directly - no custom transformation needed
    # The Anthropic response object already has a content attribute
    return response




async def read_history_from_file(file_path="data/history.json"):
    """
    Read history from a JSON file or initialize empty list if file doesn't exist
    
    Args:
        file_path: Path to the history JSON file
        
    Returns:
        List containing history data
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                history = json.load(f)
            recent_history = history[-10:]
            while True:
                shall_break = True
                if recent_history[0]['role'] != 'user':
                    # move to the next as to always start with a user message
                    recent_history = recent_history[1:]
                    shall_break = False
                if not isinstance(recent_history[0]['content'], str) and recent_history[0]['content'][0]['type'] == "tool_result":
                    # history can not start with tool_result(requires tool_use to be before it), so move to the next
                    recent_history = recent_history[1:]
                    shall_break = False
                if shall_break:
                    break
                
            return recent_history
        except json.JSONDecodeError:
            logger.error(f"Error decoding {file_path}, using empty history")
            return []
    else:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        return []
    
async def write_history_to_file(history, file_path="data/history.json"):
    """
    Write history to a JSON file
    
    Args:
        history: List containing history data
        file_path: Path to the history JSON file
    """
    with open(file_path, 'w') as f:
        json.dump(history, f)
    