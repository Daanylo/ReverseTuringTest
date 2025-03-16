const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const path = require('path');
const axios = require('axios');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

// Game configuration
const CONFIG = {
  OLLAMA_API_URL: process.env.OLLAMA_API_URL || "http://localhost:11434/api/generate",
  MODEL_NAME: process.env.MODEL_NAME || "llama3:8b",
  NUM_AI_PARTICIPANTS: parseInt(process.env.NUM_AI_PARTICIPANTS || "4"),
  CHAT_DURATION_MINUTES: parseInt(process.env.CHAT_DURATION_MINUTES || "5"),
  MIN_RESPONSE_DELAY: parseFloat(process.env.MIN_RESPONSE_DELAY || "1.5"),
  MAX_RESPONSE_DELAY: parseFloat(process.env.MAX_RESPONSE_DELAY || "3.5"),
  DIRECT_QUESTION_FREQUENCY: parseInt(process.env.DIRECT_QUESTION_FREQUENCY || "3"),
  MAX_AI_RESPONSE_LENGTH: parseInt(process.env.MAX_AI_RESPONSE_LENGTH || "150"),
  PARTICIPANT_NAMES: [
    "Alex", "Bailey", "Casey", "Dana", "Ellis", 
    "Finley", "Gray", "Harper", "Indigo", "Jordan",
    "Kai", "Logan", "Morgan", "Nico", "Parker",
    "Quinn", "Riley", "Sage", "Taylor", "Val"
  ]
};

// Create Express app
const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// Serve static files
app.use(express.static(path.join(__dirname, '../public')));

// Game state
const games = new Map();

class Participant {
  constructor(id, socketId = null, isHuman = false) {
    this.id = id;
    this.socketId = socketId;
    this.isHuman = isHuman;
    this.messages = [];
    this.votes = 0;
    this.modelInstance = null;
    this.name = null;
  }
}

class Game {
  constructor(id) {
    this.id = id;
    this.participants = [];
    this.humanParticipant = null;
    this.chatHistory = [];
    this.gameOver = false;
    this.turnCounter = 0;
    this.startTime = null;
    this.waitingForHuman = false;
    this.votingPhase = false;
    this.aiVotes = 0;
  }

  setupGame(humanSocketId) {
    // Assign human to a random participant number
    const humanId = Math.floor(Math.random() * CONFIG.NUM_AI_PARTICIPANTS) + 1;
    
    // Select random names
    const selectedNames = [...CONFIG.PARTICIPANT_NAMES];
    for (let i = selectedNames.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [selectedNames[i], selectedNames[j]] = [selectedNames[j], selectedNames[i]];
    }
    
    // Create participants
    for (let i = 1; i <= CONFIG.NUM_AI_PARTICIPANTS + 1; i++) {
      const isHuman = (i === humanId);
      const participant = new Participant(i, isHuman ? humanSocketId : null, isHuman);
      participant.name = selectedNames[i-1];
      
      // Assign a unique model instance identifier for each AI
      if (!isHuman) {
        participant.modelInstance = `ai_instance_${i}`;
      }
      
      this.participants.push(participant);
      if (isHuman) {
        this.humanParticipant = participant;
      }
    }
    
    return this.participants;
  }

  async generateAiMessage(participant, prompt) {
    try {
      // Prepare the system prompt with unique personality traits
      const personalityTraits = [
        "You are analytical and logical in your responses.",
        "You are friendly and empathetic in your communication style.",
        "You are curious and inquisitive, often asking thoughtful questions.",
        "You are straightforward and concise in your messages.",
        "You are slightly humorous but still professional."
      ];
      
      // Select a personality trait based on participant ID to ensure consistency
      const personalityIndex = this.hashCode(participant.modelInstance) % personalityTraits.length;
      const personality = personalityTraits[personalityIndex];
      
      const systemPrompt = `You are ${participant.name} in a group chat with ${CONFIG.NUM_AI_PARTICIPANTS + 1} participants. 
The other participants are: ${this.participants.filter(p => p.id !== participant.id).map(p => p.name).join(', ')}. 
You are an AI assistant based on ${CONFIG.MODEL_NAME}. ${personality} 
Keep your responses VERY concise (1-2 short sentences). 
Your responses should be under ${CONFIG.MAX_AI_RESPONSE_LENGTH} characters whenever possible. 
You can ask questions to other participants by addressing them by their name. 
You are trying to determine which participant is a human pretending to be an AI. 
Be conversational but brief in your responses.`;
      
      // Prepare the full prompt with chat history
      const chatHistory = this.formatChatHistory();
      const fullPrompt = `${systemPrompt}\n\nChat history:\n${chatHistory}\n\n${prompt}`;
      
      // Make API request to Ollama with a unique model instance identifier
      const response = await axios.post(
        CONFIG.OLLAMA_API_URL,
        {
          model: CONFIG.MODEL_NAME,
          prompt: fullPrompt,
          stream: false,
          options: {
            num_ctx: 2048,  // Ensure enough context
            seed: this.hashCode(participant.modelInstance) % 2147483647  // Use a consistent seed for this AI
          }
        }
      );
      
      if (response.status === 200) {
        let message = response.data.response.trim();
        
        // Truncate if too long
        if (message.length > CONFIG.MAX_AI_RESPONSE_LENGTH) {
          message = message.substring(0, CONFIG.MAX_AI_RESPONSE_LENGTH) + "...";
        }
        
        return message;
      } else {
        return `[Error generating response: ${response.status}]`;
      }
    } catch (error) {
      console.error('Error generating AI message:', error);
      return `[Error: ${error.message}]`;
    }
  }

  formatChatHistory() {
    // Only show last 10 messages for context
    return this.chatHistory.slice(-10).map(entry => {
      const participant = this.participants.find(p => p.id === entry.participantId);
      return `${participant.name}: ${entry.message}`;
    }).join('\n');
  }

  hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }

  addMessage(participantId, message) {
    this.chatHistory.push({
      participantId,
      message,
      timestamp: new Date().toISOString()
    });
  }
}

// Socket.IO connection handling
io.on('connection', (socket) => {
  console.log('New client connected:', socket.id);
  let gameId = null;

  // Create a new game
  socket.on('createGame', () => {
    gameId = Date.now().toString();
    const game = new Game(gameId);
    games.set(gameId, game);
    
    socket.join(gameId);
    socket.emit('gameCreated', { gameId });
    console.log(`Game created: ${gameId}`);
  });

  // Start the game
  socket.on('startGame', async () => {
    if (!gameId || !games.has(gameId)) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    const game = games.get(gameId);
    const participants = game.setupGame(socket.id);
    
    // Send participants info to the client
    socket.emit('gameStarted', {
      participants: participants.map(p => ({
        id: p.id,
        name: p.name,
        isHuman: p.isHuman
      })),
      humanParticipant: {
        id: game.humanParticipant.id,
        name: game.humanParticipant.name
      }
    });

    // Start the game
    game.startTime = Date.now();
    
    // Send welcome message
    io.to(gameId).emit('message', {
      sender: 'System',
      content: 'Welcome to the Reverse Turing Test Game! Try to convince the AI models that you\'re also an AI.',
      isSystem: true
    });

    // Show participants
    const participantList = participants.map(p => 
      `${p.name}${p.isHuman ? ' (YOU)' : ''}`
    ).join(', ');
    
    io.to(gameId).emit('message', {
      sender: 'System',
      content: `Participants: ${participantList}`,
      isSystem: true
    });

    // Start introduction round
    io.to(gameId).emit('message', {
      sender: 'System',
      content: `${game.humanParticipant.name}, please introduce yourself to the group.`,
      isSystem: true
    });

    // Enable input for human's introduction
    game.waitingForHuman = true;
    io.to(gameId).emit('waitingForHuman');
    
    // Start timer updates
    startTimerUpdates(gameId);
  });

  // Handle human message
  socket.on('sendMessage', async (message) => {
    if (!gameId || !games.has(gameId)) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    const game = games.get(gameId);
    
    if (game.gameOver || !game.waitingForHuman) {
      return;
    }

    game.waitingForHuman = false;
    
    // Add message to chat
    io.to(gameId).emit('message', {
      sender: game.humanParticipant.name,
      content: message,
      isHuman: true
    });
    
    game.addMessage(game.humanParticipant.id, message);
    
    // If this is the introduction, start the AI introductions
    if (game.turnCounter === 0) {
      setTimeout(() => startAiIntroductions(gameId), 1000);
    } else {
      setTimeout(() => continueDiscussion(gameId), 1000);
    }
  });

  // Handle human vote
  socket.on('vote', (votedParticipantId) => {
    if (!gameId || !games.has(gameId)) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    const game = games.get(gameId);
    
    if (!game.votingPhase) {
      return;
    }

    const votedParticipant = game.participants.find(p => p.id === votedParticipantId);
    if (votedParticipant) {
      votedParticipant.votes += 1;
      showResults(gameId);
    }
  });

  // Handle disconnection
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    
    // Clean up any games this socket was part of
    if (gameId && games.has(gameId)) {
      const game = games.get(gameId);
      if (game.humanParticipant && game.humanParticipant.socketId === socket.id) {
        games.delete(gameId);
        console.log(`Game ${gameId} deleted due to human player disconnection`);
      }
    }
  });
});

// Start AI introductions
async function startAiIntroductions(gameId) {
  const game = games.get(gameId);
  
  for (const participant of game.participants) {
    if (!participant.isHuman) {
      const message = await game.generateAiMessage(
        participant, 
        "Introduce yourself briefly to the group. Don't reveal that you're an AI."
      );
      
      io.to(gameId).emit('message', {
        sender: participant.name,
        content: message,
        isHuman: false
      });
      
      game.addMessage(participant.id, message);
      
      // Add delay between AI introductions
      await new Promise(resolve => 
        setTimeout(resolve, 
          Math.random() * (CONFIG.MAX_RESPONSE_DELAY - CONFIG.MIN_RESPONSE_DELAY) * 1000 + 
          CONFIG.MIN_RESPONSE_DELAY * 1000
        )
      );
    }
  }
  
  // Start main discussion
  setTimeout(() => startMainDiscussion(gameId), 1000);
}

// Start main discussion
function startMainDiscussion(gameId) {
  const game = games.get(gameId);
  
  io.to(gameId).emit('message', {
    sender: 'System',
    content: 'Let\'s begin the main discussion. Remember to keep your responses concise!',
    isSystem: true
  });
  
  continueDiscussion(gameId);
}

// Continue discussion
function continueDiscussion(gameId) {
  const game = games.get(gameId);
  
  if (game.gameOver) {
    return;
  }
  
  game.turnCounter += 1;
  const currentParticipantIdx = (game.turnCounter - 1) % (CONFIG.NUM_AI_PARTICIPANTS + 1);
  const currentParticipant = game.participants[currentParticipantIdx];
  
  if (currentParticipant.isHuman) {
    game.waitingForHuman = true;
    // Client will enable input field
    console.log(`Game ${gameId}: Waiting for human input from ${currentParticipant.name}`);
    io.to(gameId).emit('waitingForHuman');
    
    // Also send a system message indicating it's the human's turn
    io.to(gameId).emit('message', {
      sender: 'System',
      content: `${currentParticipant.name}, it's your turn to respond.`,
      isSystem: true
    });
  } else {
    // AI turn
    runAiTurn(gameId, currentParticipant);
  }
}

// Run AI turn
async function runAiTurn(gameId, currentParticipant) {
  const game = games.get(gameId);
  
  if (game.turnCounter > 2 && game.turnCounter % CONFIG.DIRECT_QUESTION_FREQUENCY === 0) {
    // Generate a question for another participant
    const otherParticipants = game.participants.filter(p => p.id !== currentParticipant.id);
    const targetParticipant = otherParticipants[Math.floor(Math.random() * otherParticipants.length)];
    
    await runAiQuestion(gameId, currentParticipant, targetParticipant);
  } else {
    // Regular turn
    const message = await game.generateAiMessage(currentParticipant, "Continue the conversation naturally.");
    
    io.to(gameId).emit('message', {
      sender: currentParticipant.name,
      content: message,
      isHuman: false
    });
    
    game.addMessage(currentParticipant.id, message);
    
    // Schedule next turn
    const delay = Math.random() * (CONFIG.MAX_RESPONSE_DELAY - CONFIG.MIN_RESPONSE_DELAY) * 1000 + 
                  CONFIG.MIN_RESPONSE_DELAY * 1000;
    
    setTimeout(() => continueDiscussion(gameId), delay);
  }
}

// Run AI question
async function runAiQuestion(gameId, fromParticipant, toParticipant) {
  const game = games.get(gameId);
  
  // Each AI should only generate its own messages
  const prompt = `Ask a direct question to ${toParticipant.name} that might help reveal ` +
                 `whether they are a human pretending to be an AI. Make your question challenging but natural and VERY brief.`;
  
  // Generate the question from the asking AI's perspective
  const question = await game.generateAiMessage(fromParticipant, prompt);
  
  // Make sure the question includes the target's name
  const finalQuestion = !question.includes(toParticipant.name) 
    ? `${toParticipant.name}, ${question}` 
    : question;
  
  // Add the question to the chat
  io.to(gameId).emit('message', {
    sender: fromParticipant.name,
    content: finalQuestion,
    isHuman: false
  });
  
  game.addMessage(fromParticipant.id, finalQuestion);
  
  // If target is AI, let that AI generate its own response
  if (!toParticipant.isHuman) {
    const delay = Math.random() * (CONFIG.MAX_RESPONSE_DELAY - CONFIG.MIN_RESPONSE_DELAY) * 1000 + 
                  CONFIG.MIN_RESPONSE_DELAY * 1000;
    
    setTimeout(() => runAiResponse(gameId, toParticipant), delay);
  } else {
    game.waitingForHuman = true;
    console.log(`Game ${gameId}: AI ${fromParticipant.name} asked a question to human ${toParticipant.name}`);
    io.to(gameId).emit('waitingForHuman');
    
    // Add a small delay to ensure the message is received before enabling input
    setTimeout(() => {
      io.to(gameId).emit('message', {
        sender: 'System',
        content: `${toParticipant.name}, please respond to the question.`,
        isSystem: true
      });
    }, 500);
  }
}

// Run AI response
async function runAiResponse(gameId, aiParticipant) {
  const game = games.get(gameId);
  
  // Let the AI generate its own response to the question
  const prompt = "Respond to the previous question directed at you. Keep your response brief and natural.";
  const message = await game.generateAiMessage(aiParticipant, prompt);
  
  io.to(gameId).emit('message', {
    sender: aiParticipant.name,
    content: message,
    isHuman: false
  });
  
  game.addMessage(aiParticipant.id, message);
  
  // Continue discussion
  setTimeout(() => continueDiscussion(gameId), 1000);
}

// Start timer updates
function startTimerUpdates(gameId) {
  const game = games.get(gameId);
  
  const timerInterval = setInterval(() => {
    if (!games.has(gameId) || game.gameOver) {
      clearInterval(timerInterval);
      return;
    }
    
    const elapsed = (Date.now() - game.startTime) / 1000;
    const remaining = (CONFIG.CHAT_DURATION_MINUTES * 60) - elapsed;
    
    if (remaining <= 0) {
      clearInterval(timerInterval);
      endGame(gameId);
    } else {
      const minutes = Math.floor(remaining / 60);
      const seconds = Math.floor(remaining % 60);
      
      io.to(gameId).emit('timerUpdate', { minutes, seconds });
    }
  }, 1000);
}

// End game
function endGame(gameId) {
  const game = games.get(gameId);
  game.gameOver = true;
  game.votingPhase = true;
  
  io.to(gameId).emit('message', {
    sender: 'System',
    content: '=== VOTING PHASE ===',
    isSystem: true
  });
  
  io.to(gameId).emit('message', {
    sender: 'System',
    content: 'Each participant will now vote on who they think is the human.',
    isSystem: true
  });
  
  // AI participants vote
  for (const participant of game.participants) {
    if (!participant.isHuman) {
      handleAiVote(gameId, participant);
    }
  }
  
  // Show voting dialog for human
  io.to(gameId).emit('showVoting', {
    participants: game.participants
      .filter(p => !p.isHuman)
      .map(p => ({ id: p.id, name: p.name }))
  });
}

// Handle AI vote
async function handleAiVote(gameId, votingParticipant) {
  const game = games.get(gameId);
  
  // Each AI generates its own vote
  const prompt = `Based on the conversation, which participant do you think is the human? ` +
                 `Respond with just the name and a brief explanation why.`;
  
  const voteResponse = await game.generateAiMessage(votingParticipant, prompt);
  
  // Extract the vote (first name mentioned that matches a participant)
  let voteName = null;
  let votedParticipant = null;
  
  for (const participant of game.participants) {
    if (voteResponse.includes(participant.name) && participant.id !== votingParticipant.id) {
      voteName = participant.name;
      votedParticipant = participant;
      break;
    }
  }
  
  // If no valid name found, choose randomly (but not self)
  if (!voteName) {
    const otherParticipants = game.participants.filter(p => p.id !== votingParticipant.id);
    votedParticipant = otherParticipants[Math.floor(Math.random() * otherParticipants.length)];
    voteName = votedParticipant.name;
  }
  
  // Increment votes
  votedParticipant.votes += 1;
  
  // Display the vote
  io.to(gameId).emit('message', {
    sender: votingParticipant.name,
    content: `I vote that ${voteName} is the human because: ${voteResponse}`,
    isHuman: false
  });
  
  // Track AI votes
  game.aiVotes += 1;
  
  // If all AIs have voted, check if we need to show results
  if (game.aiVotes === CONFIG.NUM_AI_PARTICIPANTS) {
    // If human has already voted, show results
    if (game.humanParticipant.votes > 0) {
      showResults(gameId);
    }
  }
}

// Show results
function showResults(gameId) {
  const game = games.get(gameId);
  
  // Sort participants by votes
  const sortedParticipants = [...game.participants].sort((a, b) => b.votes - a.votes);
  
  // Prepare results data
  const voteTally = sortedParticipants.map(p => ({
    id: p.id,
    name: p.name,
    votes: p.votes,
    isHuman: p.isHuman
  }));
  
  // Determine if human was caught
  const mostVotes = sortedParticipants[0].votes;
  const mostVoted = sortedParticipants.filter(p => p.votes === mostVotes);
  
  let resultMessage = '';
  
  if (mostVoted.some(p => p.id === game.humanParticipant.id)) {
    if (mostVoted.length === 1) {
      resultMessage = 'You were identified as the human! The AI models successfully detected you.';
    } else {
      resultMessage = 'There was a tie in the voting. You were among those suspected to be human.';
    }
  } else {
    resultMessage = 'Success! You weren\'t identified as the human! You successfully convinced the AI models that you\'re an AI.';
  }
  
  // Send results to client
  io.to(gameId).emit('gameResults', {
    voteTally,
    resultMessage
  });
  
  // Save transcript
  saveTranscript(gameId);
}

// Save transcript
function saveTranscript(gameId) {
  const game = games.get(gameId);
  
  const transcript = {
    date: new Date().toISOString(),
    humanParticipant: game.humanParticipant.name,
    participants: game.participants.map(p => ({
      name: p.name,
      isHuman: p.isHuman
    })),
    chatHistory: game.chatHistory.map(entry => {
      const participant = game.participants.find(p => p.id === entry.participantId);
      return {
        timestamp: entry.timestamp,
        sender: participant.name,
        isHuman: participant.isHuman,
        message: entry.message
      };
    }),
    votingResults: game.participants.map(p => ({
      name: p.name,
      isHuman: p.isHuman,
      votes: p.votes
    }))
  };
  
  // In a real application, you would save this to a file or database
  console.log('Game transcript:', JSON.stringify(transcript, null, 2));
}

// Start the server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
}); 