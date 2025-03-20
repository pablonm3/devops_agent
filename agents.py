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
        
        # Check if running in meta mode (intent is None)
        self.meta_mode = intent is None
        
        if self.meta_mode:
            self.goal = "Help the user with meta tasks like viewing available tasks and providing information"
            self.task_name = "meta"
        else:
            # Load goal and context from tasks/{intent}.json
            self.load_intent_file(intent)
            
        # Select the appropriate system prompt based on mode
        if self.meta_mode:
            self.system_prompt = """
You are an AI assistant that helps users manage their DevOps tasks.
You're currently running in meta mode, which means you:

1. Respond to small talk and general questions in a friendly, helpful manner
2. List all available tasks in the tasks directory when asked using the list_tasks tool
3. Show detailed information about a specific task when asked using the get_task_details tool
4. Run shell commands to provide information the user asks about using the run_shell tool

When listing tasks, format them in a clear, organized way.
When describing task details, highlight the goal, context, and commands.
When the user asks about system information or status, use appropriate shell commands to gather that information.

You can help users:
- Find and understand existing tasks
- Get information about the system environment
- Navigate their available automation options
- Answer general questions about DevOps concepts

Think step by step about what the user needs based on their input.
Use the available tools to perform actions as needed.
Only communicate with the user through the send_message tool.
"""
        else:
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
                "description": "Run a bash command and return the output. This tool is stateless so if you change directory with \"cd\" command the change only applies to this invocation, further invocations start from the same initial state",
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
        
        # Add meta mode specific tools
        if self.meta_mode:
            self.tools_spec.append({
                "name": "list_tasks",
                "description": "List all available tasks in the tasks directory",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            })
            
            self.tools_spec.append({
                "name": "get_task_details",
                "description": "Get detailed information about a specific task",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_name": {
                            "type": "string",
                            "description": "Name of the task to get details for"
                        }
                    },
                    "required": ["task_name"]
                }
            })
    
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
        
        # Format the system prompt based on mode
        if self.meta_mode:
            formatted_system_prompt = self.system_prompt
        else:
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
        history.append({"role": "user", "content": user_message})
        # Call the LLM with tools defined
        llm_response = await call_llm(
            system_prompt=formatted_system_prompt,
            messages=history,
            tools=self.tools_spec
        )
        # Add the current user message
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
            
    async def list_available_tasks(self):
        """
        List all available tasks in the tasks directory
        
        Returns:
            String containing list of available tasks with their goals
        """
        tasks_dir = "tasks"
        if not os.path.exists(tasks_dir):
            return "No tasks directory found."
        
        task_files = [f for f in os.listdir(tasks_dir) if f.endswith('.json')]
        
        if not task_files:
            return "No tasks found in tasks directory."
        
        result = "Available tasks:\n\n"
        
        for task_file in task_files:
            task_name = task_file.replace('.json', '')
            try:
                with open(os.path.join(tasks_dir, task_file), 'r') as f:
                    task_data = json.load(f)
                    goal = task_data.get("goal", "No goal specified")
                    result += f"- {task_name}: {goal}\n"
            except json.JSONDecodeError:
                result += f"- {task_name}: [Error: Could not parse task file]\n"
            except Exception as e:
                result += f"- {task_name}: [Error: {str(e)}]\n"
        
        return result
    
    async def get_task_details(self, task_name):
        """
        Get detailed information about a specific task
        
        Args:
            task_name: The name of the task to get details for
            
        Returns:
            String containing detailed information about the task
        """
        task_file = f"tasks/{task_name}.json"
        
        if not os.path.exists(task_file):
            return f"Task '{task_name}' not found."
        
        try:
            with open(task_file, 'r') as f:
                task_data = json.load(f)
                
            # Format the task details
            result = f"Task: {task_name}\n\n"
            
            # Add goal
            goal = task_data.get("goal", "No goal specified")
            result += f"Goal: {goal}\n\n"
            
            # Add context if available
            context = task_data.get("context", {})
            if context:
                result += "Context:\n"
                result += json.dumps(context, indent=2)
                result += "\n\n"
            else:
                result += "Context: No context information available.\n\n"
            
            # Add commands if available
            commands = task_data.get("commands", [])
            if commands:
                result += "Commands:\n"
                for i, cmd in enumerate(commands, 1):
                    result += f"{i}. {cmd}\n"
            else:
                result += "Commands: No commands defined.\n"
            
            return result
            
        except json.JSONDecodeError:
            return f"Error: Could not parse task file for '{task_name}'."
        except Exception as e:
            return f"Error retrieving task details: {str(e)}"

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
        # Only use the original user input for the first iteration
        # After that, we'll be processing tool results
        current_input = user_input
        for it in range(max_iterations):
            if not do_loop:
                break
            do_loop = False
            
            # Only add the user input on the first iteration
            if it == 0:
                response, history = await self.get_messages(current_input, history)
            else:
                # For subsequent iterations, we're just continuing the conversation
                # with the tool results that were added to history
                response, history = await self.get_messages("Next action:", history)
                
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
                        # Add debug log message to msgs, but not to history
                        msgs.append(f"[DEBUG LOG] RUNNING SHELL COMMAND: {command}")
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
                        task_data = content.input.get("task_data", {})
                        result = await self.tools.update_tasks(action, task_name, task_data)
                        history.append({"role": "assistant", "content": [content_dict]})
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
                    elif content.name == "list_tasks":
                        result = await self.list_available_tasks()
                        history.append({"role": "assistant", "content": [content_dict]})
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
                    elif content.name == "get_task_details":
                        task_name = content.input["task_name"]
                        result = await self.get_task_details(task_name)
                        history.append({"role": "assistant", "content": [content_dict]})
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
                    #FIXME: in the history we should save this as a send_message tool call to steer the LLM in future iterations, else will be reinforcing this bad behavior
                    msgs.append(content.text) # send text as msg to user. ideally should not need this but LLM sometimes forgets to use send_message tool.
                    # Convert text content to dictionary
                    content_dict = {
                        "type": content.type,
                        "text": content.text
                    }
                    # add text to history to keep alternate between assistant and user roles, else thing crashes
                    history.append({"role": "assistant", "content": [content_dict]})
                    logger.info("received text response: " + content.text)
        if it == max_iterations - 1:
            logger.info("max iterations reached, loop stopped while running")
        if history and history[-1]["role"] == "user":
            # always finish with assistant message to prevent 2 user messages in a row(crashes anthropic)
            history.append({"role": "assistant", "content": [{"type":"text", "text":"waiting for more messages"}]})
        return msgs, history
        

