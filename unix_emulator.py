"""
Unix Emulator

A simple emulator for Unix commands that simulates an Ubuntu server environment.
"""
import os
import re
from typing import Dict, List, Callable, Optional, Any, Union


class UnixEmulator:
    """A simple emulator for Unix commands that simulates an Ubuntu server environment."""
    
    def __init__(self, file_system: Optional[Dict[str, Any]] = None, custom_commands: Optional[Dict[str, Callable]] = None):
        """
        Initialize the Unix emulator.
        
        Args:
            file_system: Optional dictionary representing the initial file system structure.
                         If None, a default file system with /home/pablo/motionapps is created.
            custom_commands: Optional dictionary mapping command names to handler functions.
        """
        # Initialize the file system with default structure if none provided
        if file_system is None:
            self.file_system = {
                "/": {
                    "home": {
                        "pablo": {
                            "motionapps": {}
                        }
                    }
                }
            }
        else:
            self.file_system = file_system
        
        # Set current working directory to /home/pablo
        self.current_dir = "/home/pablo"
        
        # Initialize built-in commands
        self.commands = {
            "pwd": self._pwd,
            "cd": self._cd,
            "ls": self._ls,
            "git pull": self._git_pull,
            "reboot": self._reboot,
            "sudo": self._sudo,
            "uname": self._uname,
            "whoami": self._whoami,
        }
        
        # Add custom commands if provided
        if custom_commands is not None:
            self.commands.update(custom_commands)
    
    def register_command(self, command: str, handler: Callable):
        """
        Register a new command with the emulator.
        
        Args:
            command: The command string.
            handler: The function that handles the command.
        """
        self.commands[command] = handler
    
    def execute(self, command: str) -> str:
        """
        Execute a Unix command and return the output.
        
        Args:
            command: The command to execute.
            
        Returns:
            The output of the command as a string.
            
        Raises:
            ValueError: If the command is not recognized.
        """
        # Extract the base command and arguments
        parts = command.strip().split(maxsplit=1)
        base_cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        # Special case for git commands
        if base_cmd == "git" and len(parts) > 1:
            base_cmd = f"{base_cmd} {parts[1].split()[0]}"
            args = " ".join(parts[1].split()[1:]) if len(parts[1].split()) > 1 else ""
        
        # Check if command exists
        if base_cmd in self.commands:
            return self.commands[base_cmd](args)
        
        # Check if full command exists (like "git pull")
        if command in self.commands:
            return self.commands[command]("")
        
        return f"Command not found: {base_cmd}"
    
    def _pwd(self, args: str) -> str:
        """Return the current working directory."""
        return self.current_dir
    
    def _cd(self, args: str) -> str:
        """
        Change the current working directory.
        
        Args:
            args: The target directory.
            
        Returns:
            Empty string on success or error message.
        """
        target = args.strip()
        
        if not target or target == "~":
            # cd to home directory
            self.current_dir = "/home/pablo"
            return ""
        
        if target.startswith("/"):
            # Absolute path
            new_path = target
        else:
            # Relative path
            if self.current_dir == "/":
                new_path = f"/{target}"
            else:
                new_path = f"{self.current_dir}/{target}"
        
        # Resolve .. in path
        parts = new_path.split("/")
        resolved_parts = []
        for part in parts:
            if part == "" or part == ".":
                continue
            elif part == "..":
                if resolved_parts:
                    resolved_parts.pop()
            else:
                resolved_parts.append(part)
        
        new_path = "/" + "/".join(resolved_parts)
        
        # Check if the path exists in the file system
        if self._path_exists(new_path):
            self.current_dir = new_path
            return ""
        else:
            return f"bash: cd: {target}: No such file or directory"
    
    def _ls(self, args: str) -> str:
        """
        List directory contents.
        
        Args:
            args: Command arguments like path or options.
            
        Returns:
            Directory listing as a string.
        """
        # Parse arguments
        show_hidden = "-a" in args
        
        # Determine target directory
        target_dir = self.current_dir
        args_parts = args.split()
        for part in args_parts:
            if not part.startswith("-"):
                if part.startswith("/"):
                    target_dir = part
                else:
                    if self.current_dir == "/":
                        target_dir = f"/{part}"
                    else:
                        target_dir = f"{self.current_dir}/{part}"
                break
        
        # Get the directory contents
        dir_contents = self._get_dir_contents(target_dir)
        if isinstance(dir_contents, str):
            return dir_contents  # Error message
        
        # Filter out hidden files if not showing them
        if not show_hidden:
            dir_contents = [item for item in dir_contents if not item.startswith(".")]
        
        # Format and return the result
        return "  ".join(sorted(dir_contents))
    
    def _git_pull(self, args: str) -> str:
        """
        Simulate the git pull command.
        
        Args:
            args: The arguments for the git pull command.
            
        Returns:
            A string indicating the result of the operation.
        """
        return "Already up to date."
    
    def _reboot(self, args: str) -> str:
        """
        Simulate the reboot command. Requires sudo privileges.
        
        Args:
            args: The arguments for the reboot command.
            
        Returns:
            A string indicating the result of the operation.
        """
        # When called directly without sudo prefix
        return "Operation not permitted, must be run with sudo to work"
    
    def _sudo(self, args: str) -> str:
        """
        Handle sudo commands.
        
        Args:
            args: The command to run with sudo.
            
        Returns:
            The result of the sudoed command.
        """
        # Extract the command to run with sudo
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return "Usage: sudo command [arguments]"
            
        sudo_cmd = parts[0]
        sudo_args = parts[1] if len(parts) > 1 else ""
        
        # Handle sudo reboot
        if sudo_cmd == "reboot":
            return "System is rebooting..."
            
        # For other sudo commands
        return f"sudo: command not found: {sudo_cmd}"
    
    def _uname(self, args: str) -> str:
        """
        Simulate the uname command on an Ubuntu server.
        
        Args:
            args: Arguments for the uname command (e.g., -a for all information)
            
        Returns:
            String output simulating an Ubuntu server's uname response
        """
        # Default Ubuntu server output for uname -a 
        if args.strip() == "-a":
            return "Linux ubuntu-server 5.15.0-92-generic #102-Ubuntu SMP Wed Jan 10 09:33:48 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux"
        # Basic uname with no flags just returns "Linux"
        elif not args.strip():
            return "Linux"
        # Handle other common flags
        elif args.strip() == "-s":
            return "Linux"  # Kernel name
        elif args.strip() == "-n":
            return "ubuntu-server"  # Network node hostname
        elif args.strip() == "-r":
            return "5.15.0-92-generic"  # Kernel release
        elif args.strip() == "-v":
            return "#102-Ubuntu SMP Wed Jan 10 09:33:48 UTC 2024"  # Kernel version
        elif args.strip() == "-m":
            return "x86_64"  # Machine hardware name
        elif args.strip() == "-p":
            return "x86_64"  # Processor type
        elif args.strip() == "-i":
            return "x86_64"  # Hardware platform
        elif args.strip() == "-o":
            return "GNU/Linux"  # Operating system
        else:
            return f"uname: invalid option -- '{args.strip()}'\nTry 'uname --help' for more information."
    
    def _whoami(self, args: str) -> str:
        """
        Simulate the whoami command which displays the current user.
        
        Args:
            args: Arguments for the whoami command (usually empty)
            
        Returns:
            String representing the current username
        """
        # For this emulation, we'll always return 'pablo' as the username
        # to match the default home directory structure
        return "pablo"
    
    def _path_exists(self, path: str) -> bool:
        """
        Check if a path exists in the file system.
        
        Args:
            path: The path to check.
            
        Returns:
            True if the path exists, False otherwise.
        """
        if path == "/":
            return True
        
        parts = path.strip("/").split("/")
        current = self.file_system["/"]
        
        for part in parts:
            if part not in current:
                return False
            current = current[part]
        
        return True
    
    def _get_dir_contents(self, path: str) -> Union[List[str], str]:
        """
        Get the contents of a directory.
        
        Args:
            path: The path to the directory.
            
        Returns:
            List of directory entries or error message as string.
        """
        if not self._path_exists(path):
            return f"ls: cannot access '{path}': No such file or directory"
        
        parts = path.strip("/").split("/")
        current = self.file_system["/"]
        
        for part in parts:
            if part:
                if part not in current:
                    return f"ls: cannot access '{path}': No such file or directory"
                current = current[part]
        
        # Return list of keys in dictionary, which represent files and directories
        return list(current.keys())
    
    def add_file(self, path: str, content: Optional[Dict[str, Any]] = None):
        """
        Add a file or directory to the file system.
        
        Args:
            path: Path to the file or directory.
            content: Content of the file/directory. Empty dict for directories.
        """
        if content is None:
            content = {}
        
        parts = path.strip("/").split("/")
        filename = parts.pop()
        
        # Navigate to parent directory
        current = self.file_system["/"]
        for part in parts:
            if part:
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        # Add file/directory
        current[filename] = content
    
    def remove_file(self, path: str) -> bool:
        """
        Remove a file or directory from the file system.
        
        Args:
            path: Path to the file or directory.
            
        Returns:
            True if successful, False otherwise.
        """
        parts = path.strip("/").split("/")
        filename = parts.pop()
        
        # Navigate to parent directory
        current = self.file_system["/"]
        for part in parts:
            if part:
                if part not in current:
                    return False
                current = current[part]
        
        # Remove file/directory
        if filename in current:
            del current[filename]
            return True
        
        return False


# Example usage
if __name__ == "__main__":
    # Create an emulator instance
    emulator = UnixEmulator()
    
    # Define a custom command
    def echo_command(args):
        return args
    
    emulator.register_command("echo", echo_command)
    
    # Add some files to the file system
    emulator.add_file("/home/pablo/motionapps/README.md")
    emulator.add_file("/home/pablo/motionapps/.git")
    emulator.add_file("/home/pablo/motionapps/src", {})
    emulator.add_file("/home/pablo/motionapps/src/main.py")
    
    # Run some commands
    print(f"$ pwd\n{emulator.execute('pwd')}")
    print(f"$ ls\n{emulator.execute('ls')}")
    print(f"$ cd motionapps\n{emulator.execute('cd motionapps')}")
    print(f"$ pwd\n{emulator.execute('pwd')}")
    print(f"$ ls\n{emulator.execute('ls')}")
    print(f"$ ls -a\n{emulator.execute('ls -a')}")
    print(f"$ git pull\n{emulator.execute('git pull')}")
    print(f"$ cd /\n{emulator.execute('cd /')}")
    print(f"$ pwd\n{emulator.execute('pwd')}")
