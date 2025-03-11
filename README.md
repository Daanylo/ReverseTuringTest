# Reverse Turing Test Game

This game challenges you to convince 4 AI models that you're also an AI by participating in a group chat. The AI models will chat with each other and ask questions, and at the end, everyone votes on who they think is the human imposter.

## Requirements

- Python 3.8+
- Ollama with Llama 3.1 installed

## Setup

1. Make sure you have Ollama installed with Llama 3.1:
   ```
   ollama pull llama3.1
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Run the game:
   ```
   python reverse_turing_test.py
   ```
   
   Or use the provided scripts:
   - Windows: `run_game.bat`
   - Linux/Mac: `./run_game.sh`

## How to Play

1. You'll be assigned a random name (instead of a participant number).
2. The AI models will chat with each other, and you'll need to respond when addressed.
3. When someone mentions your name, it will be highlighted to make it easier to notice.
4. Try to mimic AI responses to blend in with the other participants.
5. The AIs are instructed to keep their responses short, so you should do the same.
6. After a set time, everyone will vote on who they think is the human.
7. The game ends with the reveal of whether the AIs correctly identified you.

## Configuration

You can customize the game by editing the `config.py` file:
- Change the game duration
- Adjust the number of AI participants
- Modify AI response timing
- Toggle debug mode
- And more!

## Game Transcript

After each game, a transcript is saved to a text file that includes:
- All participants and their roles
- The complete chat history
- Voting results

Good luck convincing the AIs that you're one of them! 