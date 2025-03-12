from global_utils import get_logger
import io
import os
import json
from openai import AsyncOpenAI
import anthropic
from utils import call_llm, read_history_from_file, write_history_to_file
from agents import Agent
# Set up logger
logger = get_logger(__name__)

# Initialize OpenAI client
async_openai_client = AsyncOpenAI()

async def get_transcription(downloaded_file, file_name):
    """
    Transcribe an audio file using OpenAI's Whisper model
    
    Args:
        downloaded_file: The binary content of the audio file
        file_name: The name of the file including extension
        
    Returns:
        The transcribed text as a string
    """
    buffer = io.BytesIO(downloaded_file)
    buffer.name = file_name  # this is the important line
    transcription = await async_openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=buffer,
    )
    return transcription.text 

async def classify_context(text, history):
    # Load intents dynamically from all JSON files in the tasks directory
    intents = []
    tasks_dir = "tasks"
    
    try:
        for filename in os.listdir(tasks_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(tasks_dir, filename)
                with open(file_path, 'r') as f:
                    task_data = json.load(f)
                    if 'intent_name' in task_data and 'intent_name' in task_data:
                        intents.append({
                            "intent_name": task_data['intent_name'],
                            "goal": task_data['goal']
                        })
    except Exception as e:
        logger.error(f"Error loading intent files: {e}")
        # Fallback to default intent if there's an error
        raise e
    intents_str = ""
    for intent in intents:
        intents_str += f"{intent['intent_name']}: {intent['goal']}\n"
    
    SYSTEM_PROMPT = f"""
You are a devops assistant, given a convesation with a user, predict the latest intent of the user among the following options:
{intents_str}\n
Look at the last message in the context of the entire conversation to predict most recent intent.
First think step by step and output the intent between <intent> and </intent> tags.if no match output <intent>NA</intent>
    """
    messages = history +[{"role": "user", "content": text}]
    r = await call_llm(SYSTEM_PROMPT, messages)
    r = r.content[0].text
    
    # Handle both string and tool call responses
    if isinstance(r, dict) and r.get("type") == "tool_use":
        # This shouldn't happen for classification, but handle just in case
        logger.warning("Unexpected tool call in classification")
        raise Exception("Unexpected tool call in classification")
    
    logger.info(f"Classification result: {r}")
    
    # Extract intent from the response
    intent = "NA"
    if "<intent>" in r and "</intent>" in r:
        intent = r.split("<intent>")[1].split("</intent>")[0]
    if intent == "NA":
        logger.info("No intent found, returning generic response")
        return None
        
    return intent

async def process_text(text, test_mode=False):
    # Read history from file or initialize empty list if file doesn't exist
    history = await read_history_from_file()
    
    # Check if the last item in history has a role of "user"
    # If so, add a new assistant message to prevent crash
    if history and history[-1]["role"] == "user":
        logger.info("Last history item is from user, adding assistant response to maintain conversation flow")
        history.append({
            "role": "assistant", 
            "content": [{"type": "text", "text": "I'm listening, how can I help you?"}]
        })
    
    # Get classification for the user input
    classification = await classify_context(text, history)

    if classification is None:
        logger.info("No intent found, returning generic response")
        return ["Intent not identified, I'm your devops assistant, ask me to create, edit or remove a devops task or to execute an existing devops task"]
    
    # Initialize agent with the classified intent as goal
    agent = Agent(intent=classification, test_mode=test_mode)
    
    # Run the agent loop
    responses, new_history = await agent.run_agent_loop(text, history)

    await write_history_to_file(new_history)
    
    return responses