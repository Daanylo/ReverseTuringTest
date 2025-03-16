# Game Configuration Settings

# Ollama API settings
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:12b"

# Game settings
NUM_AI_PARTICIPANTS = 4  # Number of AI participants
CHAT_DURATION_MINUTES = 5  # Duration of the chat in minutes
MAX_TURNS = 50  # Maximum number of turns (as a fallback if time-based ending doesn't work)

# AI behavior settings
MIN_RESPONSE_DELAY = 1.5  # Minimum delay between AI responses (seconds)
MAX_RESPONSE_DELAY = 3.5  # Maximum delay between AI responses (seconds)
DIRECT_QUESTION_FREQUENCY = 3  # How often AIs ask direct questions (every N turns)
MAX_AI_RESPONSE_LENGTH = 150  # Maximum length of AI responses in characters

# Display settings
SHOW_TIMESTAMPS = True  # Whether to show timestamps in the chat
DEBUG_MODE = False  # Enable debug mode for additional logging
USE_RANDOM_NAMES = True  # Use random names instead of participant numbers

# List of possible participant names
PARTICIPANT_NAMES = [
    "Alex", "Bailey", "Casey", "Dana", "Ellis", 
    "Finley", "Gray", "Harper", "Indigo", "Jordan",
    "Kai", "Logan", "Morgan", "Nico", "Parker",
    "Quinn", "Riley", "Sage", "Taylor", "Val"
] 