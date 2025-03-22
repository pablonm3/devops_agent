# DevOps Agent - Telegram Control Bot

A powerful DevOps assistant that allows you to control your Mac or Linux machine remotely via Telegram. Create custom automation tasks and execute commands seamlessly from your phone or any device with Telegram.

## Features

- 🤖 Control your machine remotely via Telegram
- 🔊 Send voice messages for hands-free operation (transcription via Whisper API)
- 🛠️ Create, edit, and manage custom automation tasks
- 🖥️ Run shell commands on your machine
- 🔒 Secure access limited to authorized Telegram user ID
- 🧠 Powered by Claude AI (Anthropic) for natural language understanding

## Demo

Watch the video demonstration:

[![DevOps Agent Demo](https://img.youtube.com/vi/ElWG1wArY5I/0.jpg)](https://youtu.be/ElWG1wArY5I)

## Requirements

- Python 3.10+
- Conda (recommended for environment management)
- Mac or Linux machine
- Telegram account
- Anthropic API key (for Claude)
- OpenAI API key (for Whisper transcription)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/devops_agent.git
cd devops_agent
```

2. Set up the environment:

```bash
conda env create -f environment.yml
conda activate devops_agent
```

3. Configure your environment variables (see Configuration section below)

## Setting Up Your Telegram Bot

1. Open Telegram and search for "BotFather" (@BotFather)
2. Send the command `/newbot` to BotFather
3. Follow the instructions to name your bot and create a username for it
4. Once created, BotFather will provide you with a **token** that looks like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`
5. Save this token as you'll need it for configuration

## Configuration

Create a `.env` file in the root directory with the following variables:

```
TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
TELEGRAM_USER_ID="your_telegram_user_id" 
ANTHROPIC_API_KEY="your_anthropic_api_key"
OPENAI_API_KEY="your_openai_api_key"
LLM_MODEL="claude-3-7-sonnet-20250219"
```

To find your Telegram user ID:
1. Send a message to @userinfobot on Telegram
2. It will reply with your user ID

## Running the Bot

### Telegram Bot

To start the Telegram bot:

```bash
python telegram_bot.py
```

### CLI Bot (local usage)

For local command line usage:

```bash
python cli_bot.py
```

## Usage

Once your bot is running, you can:

1. Send text messages to the bot with commands or questions
2. Send voice messages that will be transcribed and processed
3. Create custom tasks by sending a message like "Create a task to check system status"
4. Run shell commands by asking the bot to perform specific actions
5. Get help by asking the bot about its capabilities

## Security Considerations

- The bot only responds to the Telegram user ID specified in your `.env` file
- API keys should be kept secret and never committed to version control
- The bot can execute shell commands on your machine, so ensure it's running in a secure environment
- Consider using a restricted user account for running the bot in production

## Creating Custom Tasks

You can create custom automation tasks that can be executed later:

1. Ask the bot to create a new task: "Create a task called check_disk that checks disk space"
2. The bot will help you define the steps and commands for the task
3. Once created, you can run the task by name: "Run check_disk task"

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 