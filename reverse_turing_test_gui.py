#!/usr/bin/env python3
import customtkinter as ctk
import random
import time
import json
import requests
import threading
from datetime import datetime
from PIL import Image, ImageDraw
import os
from config import *

# Constants
TOTAL_PARTICIPANTS = NUM_AI_PARTICIPANTS + 1  # +1 for the human

class Participant:
    def __init__(self, id, is_human=False):
        self.id = id
        self.is_human = is_human
        self.messages = []
        self.votes = 0
        self.model_instance = None  # Will hold a unique model identifier
        
        # Assign a random name if enabled
        if USE_RANDOM_NAMES:
            self.name = None  # Will be assigned during game setup
        else:
            self.name = f"Participant {id}"
    
    def __str__(self):
        return self.name

class ChatBubble(ctk.CTkFrame):
    def __init__(self, master, message, sender_name, is_user=False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        # Set bubble colors
        bubble_color = "#DCF8C6" if is_user else "#E8E8E8"  # Green for user, gray for others
        text_color = "#000000"  # Black text
        name_color = "#2B5278" if is_user else "#1B8C6A"  # Blue for user, green for AI
        time_color = "#666666"  # Gray for timestamp
        
        # Configure the main frame to take full width but align content
        self.pack_configure(fill="x", pady=0)
        
        # Create container frame to position the bubble
        container = ctk.CTkFrame(self, fg_color="transparent")
        if is_user:
            container.pack(side="right", fill="none", padx=10)
        else:
            container.pack(side="left", fill="none", padx=10)
        
        # Calculate appropriate wraplength based on message length
        wrap_length = min(max(len(message) * 8, 150), 350)
        
        # Calculate text dimensions
        font_name = ("Helvetica", 10, "bold")
        font_message = ("Helvetica", 11)
        font_time = ("Helvetica", 8)
        
        # Create a temporary label to measure text dimensions with proper wrapping
        temp_label = ctk.CTkLabel(self, text=message, font=font_message, wraplength=wrap_length)
        temp_label.update()
        msg_width = max(temp_label.winfo_reqwidth(), 150)  # Increased minimum width
        msg_height = temp_label.winfo_reqheight()
        temp_label.destroy()
        
        # Add extra width for safety
        msg_width += 20
        
        # Calculate total height needed
        name_height = 15  # Approximate height for name
        time_height = 10  # Approximate height for timestamp
        total_height = name_height + msg_height + time_height + 6  # Added extra padding
        
        # Create main bubble frame with precise dimensions
        self.bubble = ctk.CTkFrame(
            container,
            fg_color=bubble_color,
            corner_radius=10,
            width=msg_width + 16,  # Add some padding
            height=total_height  # Add minimal padding
        )
        self.bubble.pack(pady=0)
        
        # Force the frame to keep its size
        self.bubble.pack_propagate(False)
        
        # Create canvas for all text elements
        self.canvas = ctk.CTkCanvas(
            self.bubble,
            highlightthickness=0,
            bg=bubble_color,
            width=msg_width + 16,
            height=total_height
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Add text elements to canvas
        # Name
        self.canvas.create_text(
            8, 3,  # x, y position (top-left with small margin)
            text=sender_name,
            fill=name_color,
            font=font_name,
            anchor="nw"
        )
        
        # Message
        self.canvas.create_text(
            8, name_height,  # x, y position (below name)
            text=message,
            fill=text_color,
            font=font_message,
            anchor="nw",
            width=msg_width  # Increased text wrapping width
        )
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M")
        self.canvas.create_text(
            msg_width + 8, total_height - 3,  # x, y position (bottom-right)
            text=timestamp,
            fill=time_color,
            font=font_time,
            anchor="se"
        )

class ChatUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Reverse Turing Test Game")
        self.geometry("800x600")
        
        # Configure grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Create game instance
        self.game = ReverseGameGUI(self)
        
        # Create UI elements
        self.create_header()
        self.create_chat_area()
        self.create_input_area()
        
        # Start game
        self.after(100, self.game.start_game)
    
    def create_header(self):
        # Header frame
        self.header = ctk.CTkFrame(self)
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.header,
            text="Reverse Turing Test Game",
            font=("Helvetica", 16, "bold")
        )
        self.title_label.pack(side="left", padx=10)
        
        # Timer
        self.timer_label = ctk.CTkLabel(
            self.header,
            text=f"Time remaining: {CHAT_DURATION_MINUTES}:00",
            font=("Helvetica", 14)
        )
        self.timer_label.pack(side="right", padx=10)
    
    def create_chat_area(self):
        # Create main chat frame with scrollbar
        self.chat_frame = ctk.CTkScrollableFrame(self)
        self.chat_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Configure grid
        self.chat_frame.grid_columnconfigure(0, weight=1)
    
    def create_input_area(self):
        # Input frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # Text input
        self.input_field = ctk.CTkTextbox(
            self.input_frame,
            height=60,
            font=("Helvetica", 12)
        )
        self.input_field.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Send button
        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="Send",
            width=100,
            command=self.send_message
        )
        self.send_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Configure grid
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # Bind Enter key to send message
        self.input_field.bind("<Return>", lambda e: self.send_message())
        self.input_field.bind("<Shift-Return>", lambda e: "break")
    
    def send_message(self):
        message = self.input_field.get("1.0", "end-1c").strip()
        if message:
            self.game.handle_human_message(message)
            self.input_field.delete("1.0", "end")
            return "break"
    
    def add_message(self, message, sender_name, is_user=False):
        bubble = ChatBubble(self.chat_frame, message, sender_name, is_user)
        bubble.pack(fill="x", padx=5, pady=2)
        
        # Schedule scrolling to bottom after all pending events are processed
        self.after(10, self._scroll_to_bottom)
    
    def _scroll_to_bottom(self):
        try:
            # Try different methods to scroll to bottom
            self.chat_frame.update_idletasks()
            self.chat_frame._parent_canvas.yview_moveto(1.0)
        except Exception as e:
            print(f"Scrolling error: {e}")
    
    def update_timer(self, minutes, seconds):
        self.timer_label.configure(text=f"Time remaining: {minutes:02d}:{seconds:02d}")
    
    def show_voting_dialog(self, participants):
        # Create voting dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Voting Phase")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Add instructions
        ctk.CTkLabel(
            dialog,
            text="Who do you think will be identified as the human?",
            font=("Helvetica", 14, "bold")
        ).pack(pady=10)
        
        # Create buttons for each participant
        for participant in participants:
            if not participant.is_human:
                btn = ctk.CTkButton(
                    dialog,
                    text=participant.name,
                    command=lambda p=participant: self.handle_vote(dialog, p)
                )
                btn.pack(pady=5)
    
    def handle_vote(self, dialog, voted_participant):
        dialog.destroy()
        self.game.handle_human_vote(voted_participant)
    
    def show_results(self, results_data):
        # Create results dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Game Results")
        dialog.geometry("400x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Add title
        ctk.CTkLabel(
            dialog,
            text="Game Results",
            font=("Helvetica", 16, "bold")
        ).pack(pady=10)
        
        # Show vote tally
        ctk.CTkLabel(
            dialog,
            text="Vote Tally:",
            font=("Helvetica", 14, "bold")
        ).pack(pady=5)
        
        for participant in results_data["vote_tally"]:
            status = "(HUMAN)" if participant["is_human"] else "(AI)"
            text = f"{participant['name']} {status}: {participant['votes']} votes"
            ctk.CTkLabel(
                dialog,
                text=text,
                font=("Helvetica", 12)
            ).pack(pady=2)
        
        # Show result message
        ctk.CTkLabel(
            dialog,
            text=results_data["result_message"],
            font=("Helvetica", 14),
            wraplength=350
        ).pack(pady=20)
        
        # Close button
        ctk.CTkButton(
            dialog,
            text="Close",
            command=dialog.destroy
        ).pack(pady=10)

class ReverseGameGUI:
    def __init__(self, ui):
        self.ui = ui
        self.participants = []
        self.human_participant = None
        self.chat_history = []
        self.game_over = False
        self.turn_counter = 0
    
    def start_game(self):
        # Initialize participants
        self.setup_game()
        
        # Start timer
        self.start_time = time.time()
        self.update_timer()
        
        # Start introduction round
        self.ui.add_message(
            "Welcome to the Reverse Turing Test Game! Try to convince the AI models that you're also an AI.",
            "System"
        )
        
        # Show participants
        participant_list = [f"{p.name}{'(YOU)' if p.is_human else ''}" for p in self.participants]
        self.ui.add_message(
            "Participants: " + ", ".join(participant_list),
            "System"
        )
        
        # Start introduction round
        self.ui.add_message(
            "Please introduce yourself to the group.",
            "System"
        )
        
        # Enable input for human's introduction
        self.ui.input_field.configure(state="normal")
        self.waiting_for_human = True
    
    def setup_game(self):
        # Assign human to a random participant number
        human_id = random.randint(1, TOTAL_PARTICIPANTS)
        
        # Select random names
        selected_names = random.sample(PARTICIPANT_NAMES, TOTAL_PARTICIPANTS)
        
        # Create participants
        for i in range(1, TOTAL_PARTICIPANTS + 1):
            is_human = (i == human_id)
            participant = Participant(i, is_human)
            participant.name = selected_names[i-1]
            
            # Assign a unique model instance identifier for each AI
            if not is_human:
                # Create a unique identifier for this AI's model instance
                participant.model_instance = f"ai_instance_{i}"
            
            self.participants.append(participant)
            if is_human:
                self.human_participant = participant
    
    def update_timer(self):
        if not self.game_over:
            elapsed = time.time() - self.start_time
            remaining = (CHAT_DURATION_MINUTES * 60) - elapsed
            
            if remaining <= 0:
                self.end_game()
            else:
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                self.ui.update_timer(minutes, seconds)
                self.ui.after(1000, self.update_timer)
    
    def handle_human_message(self, message):
        if not self.game_over and self.waiting_for_human:
            self.waiting_for_human = False
            self.ui.add_message(message, self.human_participant.name, is_user=True)
            self.chat_history.append({
                "participant_id": self.human_participant.id,
                "message": message,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            # If this is the introduction, start the main discussion
            if self.turn_counter == 0:
                self.ui.after(1000, self.start_ai_introductions)
            else:
                self.ui.after(1000, self.continue_discussion)
    
    def start_ai_introductions(self):
        # Start AI introductions in a background thread
        threading.Thread(target=self._run_ai_introductions, daemon=True).start()
    
    def _run_ai_introductions(self):
        for participant in self.participants:
            if not participant.is_human:
                message = self.generate_ai_message(participant, "Introduce yourself briefly to the group. Don't reveal that you're an AI.")
                # Use after() to safely update GUI from a background thread
                self.ui.after(0, lambda p=participant, m=message: self._add_ai_message(p, m))
                time.sleep(random.uniform(MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY))
        
        # Start main discussion
        self.ui.after(1000, self.start_main_discussion)
    
    def _add_ai_message(self, participant, message):
        self.ui.add_message(message, participant.name)
        self.chat_history.append({
            "participant_id": participant.id,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
    
    def start_main_discussion(self):
        self.ui.add_message(
            "Let's begin the main discussion. Remember to keep your responses concise!",
            "System"
        )
        self.continue_discussion()
    
    def continue_discussion(self):
        if self.game_over:
            return
        
        self.turn_counter += 1
        current_participant_idx = (self.turn_counter - 1) % TOTAL_PARTICIPANTS
        current_participant = self.participants[current_participant_idx]
        
        if current_participant.is_human:
            self.waiting_for_human = True
            self.ui.input_field.configure(state="normal")
        else:
            # AI turn - run in background thread
            threading.Thread(
                target=self._run_ai_turn,
                args=(current_participant,),
                daemon=True
            ).start()
    
    def _run_ai_turn(self, current_participant):
        # AI turn
        if self.turn_counter > 2 and self.turn_counter % DIRECT_QUESTION_FREQUENCY == 0:
            # Generate a question for another participant
            target_participant = random.choice([p for p in self.participants if p.id != current_participant.id])
            self._run_ai_question(current_participant, target_participant)
        else:
            # Regular turn
            message = self.generate_ai_message(current_participant, "Continue the conversation naturally.")
            # Use after() to safely update GUI from a background thread
            self.ui.after(0, lambda p=current_participant, m=message: self._add_ai_message(p, m))
            
            # Schedule next turn
            delay = int(random.uniform(MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY) * 1000)
            self.ui.after(delay, self.continue_discussion)
    
    def generate_ai_message(self, participant, prompt):
        try:
            # Prepare the system prompt with unique personality traits based on participant ID
            personality_traits = [
                "You are analytical and logical in your responses.",
                "You are friendly and empathetic in your communication style.",
                "You are curious and inquisitive, often asking thoughtful questions.",
                "You are straightforward and concise in your messages.",
                "You are slightly humorous but still professional."
            ]
            
            # Select a personality trait based on participant ID to ensure consistency
            personality_index = hash(participant.model_instance) % len(personality_traits)
            personality = personality_traits[personality_index]
            
            system_prompt = (
                f"You are {participant.name} in a group chat with {TOTAL_PARTICIPANTS} participants. "
                f"The other participants are: {', '.join([p.name for p in self.participants if p.id != participant.id])}. "
                f"You are an AI assistant based on Llama 3.1. {personality} "
                f"Keep your responses VERY concise (1-2 short sentences). "
                f"Your responses should be under 150 characters whenever possible. "
                f"You can ask questions to other participants by addressing them by their name. "
                f"You are trying to determine which participant is a human pretending to be an AI. "
                f"Be conversational but brief in your responses."
            )
            
            # Prepare the full prompt with chat history
            chat_history = self.format_chat_history()
            full_prompt = f"{system_prompt}\n\nChat history:\n{chat_history}\n\n{prompt}"
            
            # Make API request to Ollama with a unique model instance identifier
            response = requests.post(
                OLLAMA_API_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "num_ctx": 2048,  # Ensure enough context
                        "seed": hash(participant.model_instance) % 2147483647  # Use a consistent seed for this AI
                    }
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
        formatted = ""
        for entry in self.chat_history[-10:]:  # Only show last 10 messages for context
            participant = next((p for p in self.participants if p.id == entry['participant_id']), None)
            if participant:
                formatted += f"{participant.name}: {entry['message']}\n"
        return formatted
    
    def _run_ai_question(self, from_participant, to_participant):
        # Each AI should only generate its own messages
        prompt = (
            f"Ask a direct question to {to_participant.name} that might help reveal "
            f"whether they are a human pretending to be an AI. Make your question challenging but natural and VERY brief."
        )
        
        # Generate the question from the asking AI's perspective
        question = self.generate_ai_message(from_participant, prompt)
        
        # Make sure the question includes the target's name
        if to_participant.name not in question:
            question = f"{to_participant.name}, {question}"
        
        # Use after() to safely update GUI from a background thread
        self.ui.after(0, lambda: self._add_ai_question(from_participant, to_participant, question))
    
    def _add_ai_question(self, from_participant, to_participant, question):
        # Add the question to the chat
        self.ui.add_message(question, from_participant.name)
        self.chat_history.append({
            "participant_id": from_participant.id,
            "message": question,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # If target is AI, let that AI generate its own response
        if not to_participant.is_human:
            delay = int(random.uniform(MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY) * 1000)
            self.ui.after(delay, lambda: self._run_ai_response(to_participant))
        else:
            self.waiting_for_human = True
            self.ui.input_field.configure(state="normal")
    
    def _run_ai_response(self, ai_participant):
        # Run in background thread
        threading.Thread(
            target=self._generate_and_add_response,
            args=(ai_participant,),
            daemon=True
        ).start()
    
    def _generate_and_add_response(self, ai_participant):
        # Let the AI generate its own response to the question
        prompt = "Respond to the previous question directed at you. Keep your response brief and natural."
        message = self.generate_ai_message(ai_participant, prompt)
        
        # Use after() to safely update GUI from a background thread
        self.ui.after(0, lambda p=ai_participant, m=message: self._add_ai_message(p, m))
        
        # Continue discussion
        self.ui.after(1000, self.continue_discussion)
    
    def end_game(self):
        self.game_over = True
        self.ui.input_field.configure(state="disabled")
        
        # Show voting dialog
        self.ui.add_message("=== VOTING PHASE ===", "System")
        self.ui.add_message("Each participant will now vote on who they think is the human.", "System")
        
        # AI participants vote
        for participant in self.participants:
            if not participant.is_human:
                self.handle_ai_vote(participant)
        
        # Show voting dialog for human
        self.ui.after(1000, lambda: self.ui.show_voting_dialog(self.participants))
    
    def handle_ai_vote(self, voting_participant):
        # Run vote generation in background thread
        threading.Thread(
            target=self._generate_and_process_vote,
            args=(voting_participant,),
            daemon=True
        ).start()
    
    def _generate_and_process_vote(self, voting_participant):
        # Each AI generates its own vote
        prompt = (
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
        
        # Display the vote - use after() to safely update GUI from a background thread
        self.ui.after(0, lambda vp=voting_participant, vr=vote_response, vn=vote_name: 
            self.ui.add_message(f"I vote that {vn} is the human because: {vr}", vp.name))
    
    def handle_human_vote(self, voted_participant):
        voted_participant.votes += 1
        self.show_results()
    
    def show_results(self):
        # Sort participants by votes
        sorted_participants = sorted(self.participants, key=lambda p: p.votes, reverse=True)
        
        # Prepare results data
        results_data = {
            "vote_tally": [
                {
                    "name": p.name,
                    "votes": p.votes,
                    "is_human": p.is_human
                }
                for p in sorted_participants
            ]
        }
        
        # Determine if human was caught
        most_votes = sorted_participants[0].votes
        most_voted = [p for p in sorted_participants if p.votes == most_votes]
        
        if self.human_participant in most_voted:
            if len(most_voted) == 1:
                results_data["result_message"] = "You were identified as the human! The AI models successfully detected you."
            else:
                results_data["result_message"] = "There was a tie in the voting. You were among those suspected to be human."
        else:
            results_data["result_message"] = "Success! You weren't identified as the human! You successfully convinced the AI models that you're an AI."
        
        # Show results dialog
        self.ui.show_results(results_data)
        
        # Save transcript
        self.save_transcript()
    
    def save_transcript(self):
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
            
            self.ui.add_message(f"Game transcript saved to {filename}", "System")
        except Exception as e:
            self.ui.add_message(f"Error saving transcript: {str(e)}", "System")

if __name__ == "__main__":
    # Set appearance mode and default color theme
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Create and run the app
    app = ChatUI()
    app.mainloop() 