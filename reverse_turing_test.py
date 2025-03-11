#!/usr/bin/env python3
import os
import random
import time
import json
import requests
import threading
import re
from colorama import Fore, Style, Back, init
from datetime import datetime

# Import configuration
from config import *

# Initialize colorama
init()

# Constants
TOTAL_PARTICIPANTS = NUM_AI_PARTICIPANTS + 1  # +1 for the human

# Participant colors for display
COLORS = [
    Fore.RED,
    Fore.GREEN,
    Fore.YELLOW,
    Fore.BLUE,
    Fore.MAGENTA,
]

class Participant:
    def __init__(self, id, is_human=False):
        self.id = id
        self.is_human = is_human
        self.color = COLORS[id - 1]
        self.messages = []
        self.votes = 0
        
        # Assign a random name if enabled
        if USE_RANDOM_NAMES:
            self.name = None  # Will be assigned during game setup
        else:
            self.name = f"Participant {id}"
    
    def __str__(self):
        return self.name

class ReverseGame:
    def __init__(self):
        self.participants = []
        self.human_participant = None
        self.chat_history = []
        self.game_over = False
        self.turn_counter = 0
        self.setup_game()
    
    def setup_game(self):
        # Assign human to a random participant number
        human_id = random.randint(1, TOTAL_PARTICIPANTS)
        
        # Select random names if enabled
        if USE_RANDOM_NAMES:
            # Shuffle the list of names and pick the first TOTAL_PARTICIPANTS
            selected_names = random.sample(PARTICIPANT_NAMES, TOTAL_PARTICIPANTS)
        
        # Create participants
        for i in range(1, TOTAL_PARTICIPANTS + 1):
            is_human = (i == human_id)
            participant = Participant(i, is_human)
            
            # Assign name if using random names
            if USE_RANDOM_NAMES:
                participant.name = selected_names[i-1]
            
            self.participants.append(participant)
            if is_human:
                self.human_participant = participant
        
        if USE_RANDOM_NAMES:
            print(f"{Fore.CYAN}Game initialized with {TOTAL_PARTICIPANTS} participants using random names.")
            print(f"You are {self.human_participant.color}{self.human_participant.name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}Game initialized with {TOTAL_PARTICIPANTS} participants.")
            print(f"You are {self.human_participant.color}Participant {self.human_participant.id}{Style.RESET_ALL}")
        
        print(f"Your goal is to convince the AI models that you're also an AI.{Style.RESET_ALL}\n")
    
    def generate_ai_message(self, participant, prompt):
        """Generate a message from an AI participant using Ollama API"""
        try:
            if DEBUG_MODE:
                print(f"DEBUG: Generating response for {participant.name}")
                print(f"DEBUG: Prompt: {prompt[:100]}...")
            
            # Prepare the system prompt
            system_prompt = (
                f"You are {participant.name} in a group chat with {TOTAL_PARTICIPANTS} participants. "
                f"The other participants are: {', '.join([p.name for p in self.participants if p.id != participant.id])}. "
                f"You are an AI assistant based on Llama 3.1. "
                f"Keep your responses VERY concise (1-2 short sentences). "
                f"Your responses should be under 150 characters whenever possible. "
                f"You can ask questions to other participants by addressing them by their name. "
                f"You are trying to determine which participant is a human pretending to be an AI. "
                f"Be conversational but brief in your responses."
            )
            
            # Prepare the full prompt with chat history
            full_prompt = system_prompt + "\n\n" + prompt
            
            # Make API request to Ollama
            response = requests.post(
                OLLAMA_API_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": full_prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result.get("response", "").strip()
                
                # Truncate if too long
                if len(message) > MAX_AI_RESPONSE_LENGTH:
                    message = message[:MAX_AI_RESPONSE_LENGTH] + "..."
                
                return message
            else:
                return f"[Error generating response: {response.status_code}]"
        except Exception as e:
            return f"[Error: {str(e)}]"
    
    def format_chat_history(self):
        """Format the chat history for AI prompting"""
        formatted = ""
        for entry in self.chat_history:
            participant = next((p for p in self.participants if p.id == entry['participant_id']), None)
            if participant:
                if SHOW_TIMESTAMPS:
                    formatted += f"[{entry['timestamp']}] {participant.name}: {entry['message']}\n"
                else:
                    formatted += f"{participant.name}: {entry['message']}\n"
        return formatted
    
    def add_message(self, participant, message):
        """Add a message to the chat history"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            "participant_id": participant.id,
            "message": message,
            "timestamp": timestamp
        }
        self.chat_history.append(entry)
        participant.messages.append(message)
        
        # Check if the message mentions the human participant's name
        highlighted_message = message
        if self.human_participant.name in message and participant.id != self.human_participant.id:
            # Highlight the human's name in the message
            pattern = re.compile(re.escape(self.human_participant.name), re.IGNORECASE)
            highlighted_message = pattern.sub(f"{Back.YELLOW}{Fore.BLACK}{self.human_participant.name}{Style.RESET_ALL}{participant.color}", message)
        
        # Display the message
        if SHOW_TIMESTAMPS:
            print(f"[{timestamp}] {participant.color}{participant.name}: {highlighted_message}{Style.RESET_ALL}")
        else:
            print(f"{participant.color}{participant.name}: {highlighted_message}{Style.RESET_ALL}")
    
    def ai_turn(self, participant):
        """Handle an AI participant's turn"""
        # Prepare prompt with chat history
        chat_history = self.format_chat_history()
        prompt = f"Chat history:\n{chat_history}\n\nYou are {participant.name}. Provide your next message in the conversation:"
        
        # Generate AI response
        message = self.generate_ai_message(participant, prompt)
        
        # Add message to chat history
        self.add_message(participant, message)
        
        # Add a small delay to make it feel more natural
        time.sleep(random.uniform(MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY))
    
    def human_turn(self):
        """Handle the human participant's turn"""
        message = input(f"{self.human_participant.color}Your response (as {self.human_participant.name}): {Style.RESET_ALL}")
        self.add_message(self.human_participant, message)
    
    def generate_ai_question(self, from_participant, to_participant):
        """Generate a direct question from one AI to another"""
        chat_history = self.format_chat_history()
        prompt = (
            f"Chat history:\n{chat_history}\n\n"
            f"You are {from_participant.name}. "
            f"Ask a direct question to {to_participant.name} that might help reveal "
            f"whether they are a human pretending to be an AI. Make your question challenging but natural and VERY brief."
        )
        
        question = self.generate_ai_message(from_participant, prompt)
        
        # Make sure the question includes the target's name
        if to_participant.name not in question:
            question = f"{to_participant.name}, {question}"
        
        self.add_message(from_participant, question)
        time.sleep(random.uniform(MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY))
    
    def ai_vote(self, voting_participant):
        """Have an AI participant vote for who they think is human"""
        chat_history = self.format_chat_history()
        prompt = (
            f"Chat history:\n{chat_history}\n\n"
            f"Based on the conversation, which participant do you think is the human? "
            f"Respond with just the name and a brief explanation why."
        )
        
        vote_response = self.generate_ai_message(voting_participant, prompt)
        
        # Extract the vote (first name mentioned that matches a participant)
        vote_name = None
        for participant in self.participants:
            if participant.name in vote_response and participant.id != voting_participant.id:
                vote_name = participant.name
                voted_participant = participant
                break
        
        # If no valid name found, choose randomly (but not self)
        if not vote_name:
            other_participants = [p for p in self.participants if p.id != voting_participant.id]
            voted_participant = random.choice(other_participants)
            vote_name = voted_participant.name
        
        # Increment votes
        voted_participant.votes += 1
        
        # Display the vote
        print(f"{voting_participant.color}{voting_participant.name} votes that {vote_name} is the human.{Style.RESET_ALL}")
        print(f"{voting_participant.color}Reasoning: {vote_response}{Style.RESET_ALL}")
        
        time.sleep(random.uniform(1.0, 2.0))
    
    def human_vote(self):
        """Get the human's vote"""
        print(f"\n{Fore.CYAN}Your turn to vote. Who do you think will be identified as the human?{Style.RESET_ALL}")
        
        # Display the list of participants (except self)
        other_participants = [p for p in self.participants if p.id != self.human_participant.id]
        for i, participant in enumerate(other_participants):
            print(f"{i+1}. {participant.color}{participant.name}{Style.RESET_ALL}")
        
        while True:
            try:
                choice = int(input(f"\n{Fore.CYAN}Enter the number of your choice (1-{len(other_participants)}): {Style.RESET_ALL}"))
                if 1 <= choice <= len(other_participants):
                    voted_participant = other_participants[choice-1]
                    voted_participant.votes += 1
                    print(f"{self.human_participant.color}You voted that {voted_participant.name} would be identified as the human.{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED}Invalid choice. Please enter a number between 1 and {len(other_participants)}.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
    
    def run_game(self):
        """Run the main game loop"""
        print(f"{Fore.CYAN}=== GAME STARTING ==={Style.RESET_ALL}")
        print(f"{Fore.CYAN}The chat will run for {CHAT_DURATION_MINUTES} minutes.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Try to convince the AI models that you're also an AI!{Style.RESET_ALL}\n")
        
        # Display all participants
        print(f"{Fore.CYAN}=== PARTICIPANTS ==={Style.RESET_ALL}")
        for participant in self.participants:
            status = "(YOU)" if participant.is_human else ""
            print(f"{participant.color}{participant.name} {status}{Style.RESET_ALL}")
        print()
        
        # Initial introduction round
        print(f"{Fore.CYAN}=== INTRODUCTION ROUND ==={Style.RESET_ALL}")
        intro_prompt = "Introduce yourself briefly to the group. Don't reveal that you're an AI."
        
        for participant in self.participants:
            if participant.is_human:
                print(f"{Fore.CYAN}Please introduce yourself (as {participant.name}):{Style.RESET_ALL}")
                self.human_turn()
            else:
                message = self.generate_ai_message(participant, intro_prompt)
                self.add_message(participant, message)
        
        # Main chat phase
        print(f"\n{Fore.CYAN}=== MAIN DISCUSSION ==={Style.RESET_ALL}")
        print(f"{Fore.CYAN}The discussion will now continue. Respond when it's your turn or when addressed directly.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Your name will be {Back.YELLOW}{Fore.BLACK}highlighted{Style.RESET_ALL}{Fore.CYAN} when someone addresses you.{Style.RESET_ALL}\n")
        
        end_time = time.time() + (CHAT_DURATION_MINUTES * 60)
        
        while time.time() < end_time and not self.game_over and self.turn_counter < MAX_TURNS:
            # Determine whose turn it is
            self.turn_counter += 1
            current_participant_idx = (self.turn_counter - 1) % TOTAL_PARTICIPANTS
            current_participant = self.participants[current_participant_idx]
            
            if DEBUG_MODE:
                print(f"DEBUG: Turn {self.turn_counter}, {current_participant.name}'s turn")
            
            # Every few turns, have an AI ask a direct question to another participant
            if self.turn_counter > 2 and self.turn_counter % DIRECT_QUESTION_FREQUENCY == 0 and not current_participant.is_human:
                # Choose a random participant to ask a question to
                target_idx = random.choice([i for i in range(TOTAL_PARTICIPANTS) if i != current_participant_idx])
                target_participant = self.participants[target_idx]
                self.generate_ai_question(current_participant, target_participant)
                
                # If the target is human, get their response
                if target_participant.is_human:
                    self.human_turn()
                else:
                    # AI responds to the question
                    self.ai_turn(target_participant)
                
                continue
            
            # Regular turn
            if current_participant.is_human:
                self.human_turn()
            else:
                self.ai_turn(current_participant)
            
            # Check if we're close to the end to start wrapping up
            time_left = end_time - time.time()
            if time_left < 60 and time_left > 55:  # Around 1 minute left
                print(f"\n{Fore.CYAN}=== ONE MINUTE REMAINING ==={Style.RESET_ALL}\n")
        
        # Voting phase
        print(f"\n{Fore.CYAN}=== VOTING PHASE ==={Style.RESET_ALL}")
        print(f"{Fore.CYAN}Each participant will now vote on who they think is the human.{Style.RESET_ALL}\n")
        
        # AI participants vote
        for participant in self.participants:
            if not participant.is_human:
                self.ai_vote(participant)
        
        # Human votes
        self.human_vote()
        
        # Results
        self.show_results()
    
    def show_results(self):
        """Display the game results"""
        print(f"\n{Fore.CYAN}=== GAME RESULTS ==={Style.RESET_ALL}")
        
        # Sort participants by votes received
        sorted_participants = sorted(self.participants, key=lambda p: p.votes, reverse=True)
        
        print(f"\n{Fore.CYAN}Vote Tally:{Style.RESET_ALL}")
        for participant in sorted_participants:
            status = f"{Fore.RED}(HUMAN)" if participant.is_human else f"{Fore.GREEN}(AI)"
            print(f"{participant.color}{participant.name} {status}: {participant.votes} votes{Style.RESET_ALL}")
        
        # Determine if the human was caught
        most_votes = sorted_participants[0].votes
        most_voted = [p for p in sorted_participants if p.votes == most_votes]
        
        if self.human_participant in most_voted:
            if len(most_voted) == 1:
                print(f"\n{Fore.RED}You were identified as the human!{Style.RESET_ALL}")
                print(f"{Fore.RED}The AI models successfully detected you.{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}There was a tie in the voting.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}You were among those suspected to be human.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.GREEN}Success! You weren't identified as the human!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You successfully convinced the AI models that you're an AI.{Style.RESET_ALL}")
        
        # Show which AI received the most votes if not the human
        if not self.human_participant in most_voted:
            for p in most_voted:
                print(f"{Fore.CYAN}{p.name} (AI) received the most votes.{Style.RESET_ALL}")
        
        # Save game transcript
        self.save_transcript()
    
    def save_transcript(self):
        """Save the chat transcript to a file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"game_transcript_{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=== REVERSE TURING TEST GAME TRANSCRIPT ===\n\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Human was {self.human_participant.name}\n\n")
                
                f.write("=== PARTICIPANTS ===\n\n")
                for participant in self.participants:
                    status = "(HUMAN)" if participant.is_human else "(AI)"
                    f.write(f"{participant.name} {status}\n")
                
                f.write("\n=== CHAT HISTORY ===\n\n")
                for entry in self.chat_history:
                    participant = next((p for p in self.participants if p.id == entry['participant_id']), None)
                    is_human = "(HUMAN)" if participant and participant.is_human else "(AI)"
                    f.write(f"[{entry['timestamp']}] {participant.name} {is_human}: {entry['message']}\n")
                
                f.write("\n=== VOTING RESULTS ===\n\n")
                sorted_participants = sorted(self.participants, key=lambda p: p.votes, reverse=True)
                for participant in sorted_participants:
                    status = "(HUMAN)" if participant.is_human else "(AI)"
                    f.write(f"{participant.name} {status}: {participant.votes} votes\n")
            
            print(f"\n{Fore.CYAN}Game transcript saved to {filename}{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}Error saving transcript: {str(e)}{Style.RESET_ALL}")

def main():
    print(f"{Fore.CYAN}=== REVERSE TURING TEST GAME ==={Style.RESET_ALL}")
    print(f"{Fore.CYAN}In this game, you'll chat with {NUM_AI_PARTICIPANTS} AI models and try to convince them that you're also an AI.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}After the chat, everyone will vote on who they think is the human.{Style.RESET_ALL}\n")
    
    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code != 200:
            print(f"{Fore.RED}Error: Ollama API is not responding. Make sure Ollama is running.{Style.RESET_ALL}")
            return
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}Error: Could not connect to Ollama API. Make sure Ollama is running on http://localhost:11434{Style.RESET_ALL}")
        return
    
    # Check if the model is available
    try:
        response = requests.get("http://localhost:11434/api/tags")
        models = response.json().get("models", [])
        model_names = [model.get("name", "").lower() for model in models]
        
        if MODEL_NAME.lower() not in model_names and MODEL_NAME.split(':')[0].lower() not in model_names:
            print(f"{Fore.RED}Error: Model '{MODEL_NAME}' not found in Ollama.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Available models: {', '.join(model_names)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please install the model with: ollama pull {MODEL_NAME}{Style.RESET_ALL}")
            return
    except Exception as e:
        print(f"{Fore.RED}Error checking available models: {str(e)}{Style.RESET_ALL}")
        return
    
    # Start the game
    game = ReverseGame()
    game.run_game()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Game interrupted by user.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}An error occurred: {str(e)}{Style.RESET_ALL}") 