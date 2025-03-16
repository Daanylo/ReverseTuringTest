// DOM Elements
const welcomeScreen = document.getElementById('welcome-screen');
const gameScreen = document.getElementById('game-screen');
const votingScreen = document.getElementById('voting-screen');
const resultsScreen = document.getElementById('results-screen');
const startGameBtn = document.getElementById('start-game-btn');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const timerDisplay = document.getElementById('timer-display');
const votingOptions = document.getElementById('voting-options');
const resultMessage = document.getElementById('result-message');
const voteResults = document.getElementById('vote-results');
const newGameBtn = document.getElementById('new-game-btn');

// Game state
let socket;
let gameId;
let humanParticipant;
let participants = [];
let isWaitingForHuman = false;

// Initialize the game
function init() {
  // Connect to the server
  socket = io();
  
  // Set up event listeners
  setupEventListeners();
  
  // Set up socket event handlers
  setupSocketHandlers();
}

// Set up event listeners
function setupEventListeners() {
  startGameBtn.addEventListener('click', createGame);
  sendBtn.addEventListener('click', sendMessage);
  newGameBtn.addEventListener('click', resetGame);
  
  // Debug button to manually enable input
  const debugEnableBtn = document.getElementById('debug-enable-btn');
  if (debugEnableBtn) {
    debugEnableBtn.addEventListener('click', () => {
      console.log('Debug: Manually enabling input field');
      isWaitingForHuman = true;
      messageInput.disabled = false;
      sendBtn.disabled = false;
      messageInput.focus();
      messageInput.style.borderColor = 'var(--primary-color)';
      messageInput.placeholder = "Input manually enabled (debug)";
    });
  }
  
  messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  
  messageInput.addEventListener('input', () => {
    sendBtn.disabled = messageInput.value.trim() === '';
  });
}

// Set up socket event handlers
function setupSocketHandlers() {
  socket.on('gameCreated', handleGameCreated);
  socket.on('gameStarted', handleGameStarted);
  socket.on('message', handleMessage);
  socket.on('waitingForHuman', handleWaitingForHuman);
  socket.on('timerUpdate', handleTimerUpdate);
  socket.on('showVoting', handleShowVoting);
  socket.on('gameResults', handleGameResults);
  socket.on('error', handleError);
}

// Create a new game
function createGame() {
  socket.emit('createGame');
}

// Handle game created event
function handleGameCreated(data) {
  gameId = data.gameId;
  socket.emit('startGame');
}

// Handle game started event
function handleGameStarted(data) {
  participants = data.participants;
  humanParticipant = data.humanParticipant;
  
  // Switch to game screen
  showScreen(gameScreen);
  
  // Reset input field state
  messageInput.disabled = true;
  sendBtn.disabled = true;
  messageInput.value = '';
  messageInput.placeholder = "Type your message here...";
  messageInput.style.borderColor = 'var(--border-color)';
  
  // Log for debugging
  console.log('Game started - human participant:', humanParticipant);
}

// Handle message event
function handleMessage(data) {
  const { sender, content, isSystem, isHuman } = data;
  
  // Create message element
  const messageEl = document.createElement('div');
  messageEl.className = `message ${isSystem ? 'system' : isHuman ? 'user' : 'ai'}`;
  
  // Add message content
  let messageHTML = '';
  
  if (!isSystem) {
    messageHTML += `<div class="message-sender">${sender}</div>`;
  }
  
  messageHTML += `<div class="message-content">${content}</div>`;
  
  if (!isSystem) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    messageHTML += `<div class="message-time">${time}</div>`;
  }
  
  messageEl.innerHTML = messageHTML;
  
  // Add message to chat
  chatMessages.appendChild(messageEl);
  
  // Scroll to bottom
  scrollToBottom();
  
  // Highlight mentions of human's name
  if (!isSystem && !isHuman) {
    highlightMentions();
  }
}

// Handle waiting for human event
function handleWaitingForHuman() {
  isWaitingForHuman = true;
  messageInput.disabled = false;
  sendBtn.disabled = false;
  messageInput.focus();
  
  // Add visual indication that it's the user's turn
  messageInput.style.borderColor = 'var(--primary-color)';
  messageInput.placeholder = "Your turn to respond...";
  
  // Log for debugging
  console.log('Waiting for human input - input field enabled');
}

// Handle timer update event
function handleTimerUpdate(data) {
  const { minutes, seconds } = data;
  timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Handle show voting event
function handleShowVoting(data) {
  const { participants } = data;
  
  // Clear voting options
  votingOptions.innerHTML = '';
  
  // Add voting options
  participants.forEach(participant => {
    const optionEl = document.createElement('div');
    optionEl.className = 'vote-option';
    optionEl.textContent = participant.name;
    optionEl.addEventListener('click', () => {
      socket.emit('vote', participant.id);
    });
    
    votingOptions.appendChild(optionEl);
  });
  
  // Switch to voting screen
  showScreen(votingScreen);
}

// Handle game results event
function handleGameResults(data) {
  const { voteTally, resultMessage: message } = data;
  
  // Set result message
  resultMessage.textContent = message;
  
  // Clear vote results
  voteResults.innerHTML = '';
  
  // Add vote results
  voteTally.forEach(result => {
    const resultEl = document.createElement('div');
    resultEl.className = 'vote-result';
    
    const nameEl = document.createElement('div');
    nameEl.className = 'vote-result-name';
    nameEl.textContent = result.name;
    
    if (result.isHuman) {
      const badgeEl = document.createElement('span');
      badgeEl.className = 'badge human';
      badgeEl.textContent = 'HUMAN';
      nameEl.appendChild(badgeEl);
    } else {
      const badgeEl = document.createElement('span');
      badgeEl.className = 'badge ai';
      badgeEl.textContent = 'AI';
      nameEl.appendChild(badgeEl);
    }
    
    const votesEl = document.createElement('div');
    votesEl.className = 'vote-result-votes';
    votesEl.textContent = `${result.votes} vote${result.votes !== 1 ? 's' : ''}`;
    
    resultEl.appendChild(nameEl);
    resultEl.appendChild(votesEl);
    
    voteResults.appendChild(resultEl);
  });
  
  // Switch to results screen
  showScreen(resultsScreen);
}

// Handle error event
function handleError(data) {
  console.error('Error:', data.message);
  alert(`Error: ${data.message}`);
}

// Send a message
function sendMessage() {
  const message = messageInput.value.trim();
  
  if (message && isWaitingForHuman) {
    socket.emit('sendMessage', message);
    
    // Clear input and disable until next turn
    messageInput.value = '';
    messageInput.disabled = true;
    sendBtn.disabled = true;
    isWaitingForHuman = false;
    
    // Reset visual styling
    messageInput.style.borderColor = 'var(--border-color)';
    messageInput.placeholder = "Type your message here...";
    
    // Log for debugging
    console.log('Message sent - input field disabled');
  }
}

// Reset the game
function resetGame() {
  // Reload the page to start fresh
  window.location.reload();
}

// Show a specific screen
function showScreen(screen) {
  // Hide all screens
  welcomeScreen.classList.remove('active');
  gameScreen.classList.remove('active');
  votingScreen.classList.remove('active');
  resultsScreen.classList.remove('active');
  
  // Show the specified screen
  screen.classList.add('active');
}

// Scroll chat to bottom
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Highlight mentions of human's name
function highlightMentions() {
  if (!humanParticipant) return;
  
  const messages = chatMessages.querySelectorAll('.message-content');
  const name = humanParticipant.name;
  
  messages.forEach(message => {
    if (message.innerHTML.includes(name)) {
      message.innerHTML = message.innerHTML.replace(
        new RegExp(name, 'g'),
        `<span style="background-color: #ffff00; font-weight: bold;">${name}</span>`
      );
    }
  });
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', init); 