import subprocess
from global_utils import get_logger
from unix_emulator import UnixEmulator
import json
import os

logger = get_logger(__name__)

class AgentTools:
    def __init__(self, test_mode=False):
        """
        Initialize the AgentTools class
        
        Args:
            test_mode: Boolean flag to indicate if running in test mode
        """
        self.test_mode = test_mode
        self.unix_emulator = UnixEmulator()
        logger.info(f"Initialized AgentTools with test_mode={test_mode}")
    
    async def run_shell(self, command):
        """
        Run a shell command and return the output
        
        Args:
            command: Shell command to run
            
        Returns:
            Command output or error
        """
        logger.info(f"Running shell command: {command}")
        
        if self.test_mode:
            logger.info("Test mode enabled, simulating command execution")
            return self.unix_emulator.execute(command)
            
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            output = result.stdout
        else:
            output = f"Command failed with return code {result.returncode}.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        return output
    
    async def update_tasks(self, action, task_name, task_data=None):
        """
        Add, edit, or delete tasks
        
        Args:
            action: The action to perform - "add", "edit", or "delete"
            task_name: Name of the task to operate on
            task_data: Data for the task when adding or editing
            
        Returns:
            Result of the operation
        """
        file_path = f"tasks/{task_name}.json"
        logger.info(f"Performing {action} on task: {task_name}")

        task_data["intent_name"] = task_name
            
        if action == "delete":
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    return f"Task '{task_name}' deleted successfully"
                except Exception as e:
                    error_msg = f"Failed to delete task '{task_name}': {str(e)}"
                    logger.error(error_msg)
                    return error_msg
            else:
                return f"Task '{task_name}' not found"
            
        # For add or edit actions, task_data is required
        if task_data is None:
            return "Error: task_data is required for add or edit actions"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if action == "add" and os.path.exists(file_path):
            return f"Error: Task '{task_name}' already exists"
        
        if action == "edit" and not os.path.exists(file_path):
            return f"Error: Task '{task_name}' not found"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(task_data, f, indent=2)
            return f"Task '{task_name}' {action}ed successfully"
        except Exception as e:
            error_msg = f"Failed to {action} task '{task_name}': {str(e)}"
            logger.error(error_msg)
            return error_msg
