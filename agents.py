import json
import os
from global_utils import get_logger
from agent_tools import AgentTools
from utils import call_llm

logger = get_logger(__name__)

class Agent:
    def __init__(self, intent, test_mode=False):
        """
        Initialize the Agent with an intent
        
        Args:
            intent: The intent/classification that determines which task file to load
        """
        if test_mode:
            logger.info("----Agent is running in test mode----")
        self.intent = intent
        self.task_name = intent
        self.test_mode = test_mode
        self.context = {}
        self.goal = ""
        self.task_file = None
        self.tools = AgentTools(test_mode=self.test_mode)
        # Load goal and context from tasks/{intent}.json
        self.load_intent_file(intent)
        self.system_prompt = """
You are an AI assistant that helps users manage and execute commands.
Your goal is: {goal}\n\n
Current task name: {task_name}\n\n
Current context information:
{context}\n\n
{commands}\n\n
Think step by step about what you need to accomplish based on the user's input and your goal.
Use the available tools when needed to perform actions.
Before running a task that comprises multiple shell commands ask for confirmation and if user asks for changes to the commands use update_tasks tool to update the commands for the task.
You can update the context for a task at any time as you gather more information from user and from the commands you run.
Keep commands short, avoid unnecessary commands.
"""
        
        # Define tools in Anthropic's tool API format
        self.tools_spec = [
            {
                "name": "send_message",
                "description": "Send a message to the user",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message to send to the user"
                        }
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "run_shell",
                "description": "Run a bash command and return the output",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "bash command to run"
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "update_tasks",
                "description": "Add, edit, or delete tasks",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["add", "edit", "delete"],
                            "description": "Action to perform on the task"
                        },
                        "task_name": {
                            "type": "string",
                            "description": "Name of the task to operate on"
                        },
                        "task_data": {
                            "type": "object",
                            "description": "Data for the task when adding or editing, a json with props: goal, steps, context(relevant technical context like pwd, credentials, etc required to execute the task, if given extract it from the user input and also run shell commands to get it), commands(Shell commands required to perform the task, infer it from text and gather it autonomously using context and run_shell tool) and intent_description(Infer it). not required for delete"
                        }
                    },
                    "required": ["action", "task_name"]
                }
            }
        ]
    
    def load_intent_file(self, intent):
        """
        Load intent file from tasks/{intent}.json
        
        Args:
            intent: The intent to load the file for
            
        Returns:
            Boolean indicating success
        """
        file_path = f"tasks/{intent}.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    task_data = json.load(f)
                    
                self.goal = task_data.get("goal", f"Process {intent} requests")
                self.context = task_data.get("context", {})
                self.commands = task_data.get("commands", [])
                logger.info(f"Loaded intent file: {file_path}")
                return True
            except json.JSONDecodeError:
                logger.error(f"Error decoding {file_path}")
                # Fall back to using intent as goal
                self.goal = f"Process {intent} requests"
                return False
        else:
            # Fall back to using intent as goal if file doesn't exist
            logger.warning(f"Intent file not found: {file_path}, using intent as goal")
            self.goal = f"Process {intent} requests"
            return False
    
    async def load_task_file(self, task_name):
        """
        Load a task file based on the task name
        
        Args:
            task_name: Name of the task
            
        Returns:
            Boolean indicating success
        """
        file_path = f"data/task_{task_name}.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    task_data = json.load(f)
                    
                self.task_file = file_path
                self.goal = task_data.get("goal", self.goal)
                self.context = task_data.get("context", {})
                return True
            except json.JSONDecodeError:
                logger.error(f"Error decoding {file_path}")
                return False
        else:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # Create a new task file with default data
            task_data = {
                "goal": self.goal,
                "context": self.context
            }
            with open(file_path, 'w') as f:
                json.dump(task_data, f, indent=2)
            self.task_file = file_path
            return True
    
    async def get_messages(self, user_message, history):
        """
        Process user message and generate a response
        
        Args:
            user_message: Message from the user
            history: Conversation history
            
        Returns:
            Agent's response message
        """
        
        # Add the current user message
        history.append({"role": "user", "content": user_message})
        
        commands_str = ""
        if self.commands:
            commands_str = "Commands to execute:\n"
            for command in self.commands:
                commands_str += f"{command}\n"

        # Format the system prompt with the current goal and context
        formatted_system_prompt = self.system_prompt.format(
            goal=self.goal,
            task_name=self.task_name,
            context=json.dumps(self.context, indent=2),
            commands=commands_str
        )
        
        # Call the LLM with tools defined
        llm_response = await call_llm(
            system_prompt=formatted_system_prompt,
            messages=history,
            tools=self.tools_spec
        )
        
        return llm_response, history

    def save_agent_context(self, intent, context):
        """
        Save the agent context to the intent file
        
        Args:
            intent: The intent to save the context for
            context: The context information to save
        
        Returns:
            Boolean indicating success
        """
        file_path = f"tasks/{intent}.json"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Load existing data if the file exists
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    task_data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error decoding {file_path}, creating new file")
                task_data = {"goal": f"Process {intent} requests"}
        else:
            raise Exception(f"File {file_path} not found")
        
        # Update the context
        task_data["context"] = context
        
        # Write the updated data back to the file
        try:
            with open(file_path, 'w') as f:
                json.dump(task_data, f, indent=2)
            logger.info(f"Context saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving context to {file_path}: {str(e)}")
            return False
        

    async def save_task_file(self):
        """Save current goal and context to the task file"""
        if not self.task_file:
            logger.error("No task file loaded")
            return False
            
        task_data = {
            "goal": self.goal,
            "context": self.context
        }
        
        try:
            with open(self.task_file, 'w') as f:
                json.dump(task_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving task file: {e}")
            return False

    async def run_agent_loop(self, user_input, history=[]):
        """
        Run a single iteration of the agent loop
        
        Args:
            agent: Initialized Agent instance
            user_input: User's input message
            history: Conversation history (optional)
            
        Returns:
            Agent's response
        """
        max_iterations = 12
        msgs = []
        do_loop = True
        for it in range(max_iterations):
            if not do_loop:
                break
            do_loop = False
            response, history = await self.get_messages(user_input, history)
            for content in response.content:
                if content.type == "tool_use":
                    # Convert ToolUseBlock to dictionary
                    content_dict = {
                        "type": content.type,
                        "name": content.name,
                        "id": content.id,
                        "input": content.input
                    }
                    if content.name == "send_message":
                        msg = content.input["message"]
                        msgs.append(msg)
                        history.append({"role": "assistant", "content": [content_dict]})
                        #Tool response is not needed but anthropic requires we alternate between assistant and user roles, so have to add something to end with human role
                        tool_response = {
                            "role": "user",
                            "content": [
                                {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": "Message sent"
                                }
                            ]
                        }
                        history.append(tool_response)
                    elif content.name == "run_shell":
                        command = content.input["command"]
                        history.append({"role": "assistant", "content": [content_dict]})
                        output = await self.tools.run_shell(command)
                        #Tool response is not needed but anthropic requires we alternate between assistant and user roles, so have to add something to end with human role
                        tool_response = {
                            "role": "user",
                            "content": [
                                {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": output
                                }
                            ]
                        }
                        history.append(tool_response)
                        do_loop = True
                    elif content.name == "update_tasks":
                        action = content.input["action"]
                        task_name = content.input["task_name"]
                        task_data = content.input["task_data"]
                        result = await self.tools.update_tasks(action, task_name, task_data)
                        history.append({"role": "assistant", "content": [content_dict]})
                        #Tool response is not needed but anthropic requires we alternate between assistant and user roles, so have to add something to end with human role
                        tool_response = {
                            "role": "user",
                            "content": [
                                {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result
                                }
                            ]
                        }
                        history.append(tool_response)
                        do_loop = True
                elif content.type == "text":
                    # Convert text content to dictionary
                    content_dict = {
                        "type": content.type,
                        "text": content.text
                    }
                    # add text to history to keep alternate between assistant and user roles, else thing crashes
                    #history.append({"role": "assistant", "content": [content_dict]})
                    logger.info("received text response: " + content.text)
        if it == max_iterations - 1:
            logger.info("max iterations reached, loop stopped while running")
        if history and history[-1]["role"] == "user":
            # always finish with assistant message to prevent 2 user messages in a row(crashes anthropic)
            history.append({"role": "assistant", "content": [{"type":"text", "text":"waiting for more messages"}]})
        return msgs, history
        

