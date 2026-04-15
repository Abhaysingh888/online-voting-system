/* ═══════════════════════════════════════════════
   VoteSecure Pro — Master Stylesheet
   Advanced Glassmorphism + Animation System
═══════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════
   VoteSecure Pro — Main JavaScript
   Chatbot + Animations + Dark Mode + Toast
═══════════════════════════════════════════════ */

// ── Page Loader ──────────────────────────────
window.addEventListener('load', () => {
  const loader = document.getElementById('page-loader');
  if (loader) {
    setTimeout(() => loader.classList.add('hidden'), 600);
  }
});

// ── Navbar Scroll Effect ─────────────────────
const navbar = document.querySelector('.navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 40);
  });
}

// ── Dark Mode Toggle ─────────────────────────
const darkToggle = document.getElementById('dark-toggle');
const savedTheme = localStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme === 'light' ? 'light' : 'dark');
if (darkToggle) {
  darkToggle.textContent = savedTheme === 'light' ? '🌙' : '☀️';
  darkToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next    = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    darkToggle.textContent = next === 'light' ? '🌙' : '☀️';
    showToast(next === 'light' ? '☀️ Light mode on' : '🌙 Dark mode on', 'success');
  });
}

// ── Toast Notifications ──────────────────────
function showToast(message, type = 'success', duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast-item ${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${message}`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    toast.style.transition = 'all 0.4s';
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

// Auto-show Django flash messages as toasts
document.querySelectorAll('.flash-msg').forEach(msg => {
  const type = msg.classList.contains('error') ? 'error' : 'success';
  const text = msg.textContent.trim();
  if (text) showToast(text, type);
});

// ── Scroll Reveal Animation ──────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.style.opacity = '1';
      e.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.candidate-card, .stat-card, .leader-row').forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(20px)';
  el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  observer.observe(el);
});

// ── Password Strength ────────────────────────
const pwdInput  = document.getElementById('password');
const strengthBar  = document.getElementById('strength-fill');
const strengthText = document.getElementById('strength-text');

if (pwdInput && strengthBar) {
  pwdInput.addEventListener('input', () => {
    const val = pwdInput.value;
    let score = 0;
    if (val.length >= 8)            score++;
    if (/[A-Z]/.test(val))         score++;
    if (/[0-9]/.test(val))         score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;

    const levels = [
      { color: '#e74c3c', label: 'Weak',    width: '25%' },
      { color: '#e67e22', label: 'Fair',    width: '50%' },
      { color: '#f1c40f', label: 'Good',    width: '75%' },
      { color: '#27ae60', label: 'Strong ✓',width: '100%'},
    ];
    const lvl = levels[Math.max(0, score - 1)];
    if (val.length === 0) {
      strengthBar.style.width = '0';
      if (strengthText) strengthText.textContent = '';
      return;
    }
    strengthBar.style.width       = lvl.width;
    strengthBar.style.background  = lvl.color;
    if (strengthText) {
      strengthText.textContent = lvl.label;
      strengthText.style.color = lvl.color;
    }
  });
}

// ── Password Confirm Match ───────────────────
const confirmInput = document.getElementById('confirm_password');
if (confirmInput && pwdInput) {
  confirmInput.addEventListener('input', () => {
    if (confirmInput.value && confirmInput.value !== pwdInput.value) {
      confirmInput.style.borderColor = '#e74c3c';
    } else if (confirmInput.value) {
      confirmInput.style.borderColor = '#27ae60';
    } else {
      confirmInput.style.borderColor = '';
    }
  });
}

// ── Vote Confirm ─────────────────────────────
document.querySelectorAll('.vote-form').forEach(form => {
  form.addEventListener('submit', e => {
    const name = form.dataset.candidate;
    if (!confirm(`🗳️ Confirm your vote for ${name}?\n\nThis action cannot be undone.`)) {
      e.preventDefault();
    }
  });
});

// ── Particles (Home Page) ────────────────────
function createParticles() {
  const hero = document.querySelector('.hero-bg');
  if (!hero) return;
  for (let i = 0; i < 18; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const size = Math.random() * 6 + 2;
    p.style.cssText = `
      width:${size}px; height:${size}px;
      left:${Math.random()*100}%;
      animation-duration:${Math.random()*15+10}s;
      animation-delay:${Math.random()*10}s;
    `;
    hero.appendChild(p);
  }
}
createParticles();

// ── Number Counter Animation ─────────────────
function animateCounter(el) {
  const target = parseInt(el.textContent) || 0;
  if (isNaN(target) || target === 0) return;
  let current = 0;
  const step = Math.ceil(target / 40);
  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) clearInterval(timer);
  }, 35);
}
document.querySelectorAll('.stat-num').forEach(el => {
  if (/^\d+$/.test(el.textContent.trim())) animateCounter(el);
});

// ════════════════════════════════════════════
// AI CHATBOT
// ════════════════════════════════════════════

const chatKnowledge = {
  greetings: {
    patterns: ['hello','hi','hey','namaste','helo','hii'],
    response: "👋 Hello! I'm <strong>VoteBot</strong>, your AI assistant for VoteSecure. How can I help you today?<br><br>You can ask me about login, registration, or how to vote!"
  },
  login: {
    patterns: ['login','sign in','cant login','not working','password wrong','invalid','credentials'],
    response: "🔐 <strong>Login Help:</strong><br>1. Make sure username & password are correct<br>2. Check CAPS LOCK is off<br>3. Try registering if you don't have an account<br>4. Contact admin if still stuck<br><br>Need more help?"
  },
  register: {
    patterns: ['register','signup','sign up','create account','new user','join'],
    response: "📝 <strong>How to Register:</strong><br>1. Click 'Create Account' on login page<br>2. Enter username, email & password<br>3. Password must be 8+ characters<br>4. Click 'Create Account'<br>5. Login with your new credentials!"
  },
  vote: {
    patterns: ['vote','how to vote','cast vote','voting','select candidate'],
    response: "🗳️ <strong>How to Vote:</strong><br>1. Login to your account<br>2. Go to Dashboard<br>3. View all candidates<br>4. Click 'Vote for [Candidate]'<br>5. Confirm your choice<br><br>⚠️ You can only vote <strong>once</strong>!"
  },
  results: {
    patterns: ['result','results','winner','who is winning','score','count'],
    response: "📊 <strong>View Results:</strong><br>• Go to Results page after voting<br>• See live vote counts & percentages<br>• Bar chart shows comparison<br>• Leaderboard shows rankings<br><br>Results update in real-time!"
  },
  password: {
    patterns: ['forgot password','reset password','change password','password help'],
    response: "🔑 <strong>Password Help:</strong><br>• Strong password = 8+ chars + numbers + symbols<br>• If forgot: contact your system admin<br>• Admin can reset from Django Admin panel<br><br>Example: <em>MyPass@2024</em>"
  },
  security: {
    patterns: ['secure','safe','hack','private','data','csrf'],
    response: "🛡️ <strong>Security Features:</strong><br>• CSRF protection on all forms<br>• One vote per user enforced<br>• Passwords are hashed (never stored plain)<br>• Session-based authentication<br>• Django's built-in security"
  },
  admin: {
    patterns: ['admin','superuser','add candidate','manage'],
    response: "⚙️ <strong>Admin Panel:</strong><br>• Go to <code>/admin</code> in browser<br>• Login with superuser account<br>• Add/edit/delete candidates<br>• View all votes & users<br>• Manage everything from there!"
  },
  thanks: {
    patterns: ['thanks','thank you','great','helpful','awesome','perfect'],
    response: "😊 You're welcome! I'm always here to help. All the best for your vote! 🗳️"
  },
  bye: {
    patterns: ['bye','goodbye','exit','close','see you'],
    response: "👋 Goodbye! Come back anytime you need help. Happy voting! 🗳️"
  },
};

const defaultResponse = "🤔 I didn't quite understand that. Try asking about:<br>• <strong>Login issues</strong><br>• <strong>How to register</strong><br>• <strong>How to vote</strong><br>• <strong>View results</strong>";

function getBotResponse(input) {
  const lower = input.toLowerCase().trim();
  for (const key in chatKnowledge) {
    const kb = chatKnowledge[key];
    if (kb.patterns.some(p => lower.includes(p))) {
      return kb.response;
    }
  }
  return defaultResponse;
}

function appendMessage(text, sender) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${sender}`;
  bubble.innerHTML = text;
  msgs.appendChild(bubble);
  msgs.scrollTop = msgs.scrollHeight;
}

function sendMessage(text) {
  if (!text.trim()) return;
  appendMessage(text, 'user');

  // Typing indicator
  const typing = document.createElement('div');
  typing.className = 'chat-bubble bot';
  typing.innerHTML = '<em style="opacity:0.5">typing...</em>';
  typing.id = 'typing-indicator';
  document.getElementById('chat-messages').appendChild(typing);
  document.getElementById('chat-messages').scrollTop = 9999;

  setTimeout(() => {
    const t = document.getElementById('typing-indicator');
    if (t) t.remove();
    appendMessage(getBotResponse(text), 'bot');
  }, 700);

  const input = document.getElementById('chat-input');
  if (input) input.value = '';
}

// Toggle chatbot
const chatToggle = document.getElementById('chatbot-toggle');
const chatBox    = document.getElementById('chatbot-box');
if (chatToggle && chatBox) {
  chatToggle.addEventListener('click', () => {
    chatBox.classList.toggle('open');
    if (chatBox.classList.contains('open') && document.getElementById('chat-messages').children.length === 0) {
      setTimeout(() => appendMessage("👋 Hi! I'm <strong>VoteBot</strong>. How can I help you?", 'bot'), 300);
    }
  });
}

const chatCloseBtn = document.getElementById('chat-close');
if (chatCloseBtn) chatCloseBtn.addEventListener('click', () => chatBox.classList.remove('open'));

const chatSendBtn = document.getElementById('chat-send');
const chatInput   = document.getElementById('chat-input');
if (chatSendBtn) chatSendBtn.addEventListener('click', () => sendMessage(chatInput.value));
if (chatInput) {
  chatInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') sendMessage(chatInput.value);
  });
}

// Quick reply buttons
document.querySelectorAll('.quick-btn').forEach(btn => {
  btn.addEventListener('click', () => sendMessage(btn.textContent));
});