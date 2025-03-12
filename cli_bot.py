#!/usr/bin/env python3

import os
import sys
import asyncio
import logging
import readline

# Add the current directory to path for imports
sys.path.append(os.getcwd())
from global_utils import get_logger
from utils import load_env

# Set up logging
logger = get_logger(__name__)
logging.getLogger().setLevel(logging.INFO)

# Get the current directory and load .env from there
current_dir = os.path.dirname(os.path.abspath(__file__))
load_env(os.path.join(current_dir, ".env"))

from services import process_text

# Welcome message
WELCOME_MESSAGE = """
Welcome to the CLI Bot! 
To get started, type your message or use one of these commands:
/start - Display this welcome message
/quit - Exit the program
"""

TEST_MODE = False

async def process_user_input(user_input):
    """Process user input and return responses"""
    try:
        # Handle commands
        if user_input.startswith("/"):
            if user_input == "/start":
                print(WELCOME_MESSAGE)
                return
            elif user_input == "/quit":
                print("Goodbye!")
                sys.exit(0)
            else:
                print(f"Unknown command: {user_input}")
                return

        # Process text input
        print("Processing your message...")
        outputs = await process_text(user_input, test_mode=TEST_MODE)
        for output in outputs:
            print(f"\nResponse: {output}\n")
    except ValueError as e:
        print("Could not process request. The underlying LLM might be refusing to take notes on this content.")
        logger.error(f"Error processing text: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"Error: {e}")

async def main():
    """Main function to run the CLI bot"""
    print(WELCOME_MESSAGE)
    
    # Main interaction loop
    while True:
        try:
            user_input = input("You: ")
            if not user_input.strip():
                continue
                
            await process_user_input(user_input)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)
