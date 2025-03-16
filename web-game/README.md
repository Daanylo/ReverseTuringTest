# Reverse Turing Test Web Game

A web-based version of the Reverse Turing Test game where you try to convince AI participants that you're also an AI.

## Features

- Modern, responsive chat UI with text balloons
- Real-time communication using Socket.IO
- Each AI participant has a unique personality
- Highlighted mentions when an AI addresses you
- Voting system to determine if you successfully fooled the AIs
- Game transcripts saved for review

## Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)
- Ollama running locally with Llama 3 installed

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd reverse-turing-test/web-game
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env` (if not already present)
   - Modify settings in `.env` as needed

## Running the Game

1. Make sure Ollama is running with Llama 3 installed:
   ```
   ollama run llama3:8b
   ```

2. Start the web server:
   ```
   npm start
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

## How to Play

1. Click "Start Game" on the welcome screen.
2. You'll be assigned a random name and will join a chat with AI participants.
3. Introduce yourself and participate in the conversation.
4. Try to convince the AI participants that you're also an AI.
5. When the timer ends, everyone will vote on who they think is the human.
6. If you receive the most votes, you've been identified as the human and lose.
7. If someone else receives more votes, you've successfully fooled the AIs and win!

## Configuration

You can customize the game by modifying the `.env` file:

- `PORT`: The port the web server runs on
- `OLLAMA_API_URL`: URL for the Ollama API
- `MODEL_NAME`: The LLM model to use (e.g., llama3:8b)
- `NUM_AI_PARTICIPANTS`: Number of AI participants (default: 4)
- `CHAT_DURATION_MINUTES`: Length of the game in minutes (default: 5)
- `MIN_RESPONSE_DELAY`/`MAX_RESPONSE_DELAY`: Range of delay between AI responses
- `DIRECT_QUESTION_FREQUENCY`: How often AIs ask direct questions
- `MAX_AI_RESPONSE_LENGTH`: Maximum length of AI responses

## License

MIT 