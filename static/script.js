const VOTE_VALUES = ['0.5', '1', '2', '3', '5', '8'];

let ws;
let currentRoomId = window.SERVER_ROOM_ID;
let currentUsername = localStorage.getItem('scrum_username') || '';
let myUserId = localStorage.getItem('scrum_user_id');
if (!myUserId) {
    myUserId = crypto.randomUUID();
    localStorage.setItem('scrum_user_id', myUserId);
}
let roomState = null;
let myVote = null;

const joinScreen = document.getElementById('join-screen');
const gameScreen = document.getElementById('game-screen');
const usernameInput = document.getElementById('username');
const roomIdInput = document.getElementById('room-id');
const joinBtn = document.getElementById('join-btn');
const copyLinkBtn = document.getElementById('copy-link-btn');

const jiraBanner = document.getElementById('jira-banner');
const jiraSummary = document.getElementById('jira-summary');
const jiraDescription = document.getElementById('jira-description');
const jiraControls = document.getElementById('jira-controls');
const jiraKeyInput = document.getElementById('jira-key-input');
const fetchJiraBtn = document.getElementById('fetch-jira-btn');
const jiraPushControls = document.getElementById('jira-push-controls');
const jiraPointsInput = document.getElementById('jira-points-input');
const pushJiraBtn = document.getElementById('push-jira-btn');

// If URL has room, prefill
if (currentRoomId) {
    roomIdInput.value = currentRoomId;
    roomIdInput.parentElement.classList.add('hidden'); // Hide if already bound
}
if (currentUsername) {
    usernameInput.value = currentUsername;
}

joinBtn.addEventListener('click', () => {
    const name = usernameInput.value.trim();
    let room = currentRoomId || roomIdInput.value.trim() || crypto.randomUUID().split('-')[0];

    if (!name) {
        alert('Please enter your name');
        return;
    }

    currentUsername = name;
    localStorage.setItem('scrum_username', name);

    // Update URL without reload
    if (room !== currentRoomId) {
        currentRoomId = room;
        window.history.pushState({}, '', `/room/${room}`);
    }

    connectWebSocket(room, name);
});

copyLinkBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
        copyLinkBtn.textContent = '✅ Copied!';
        setTimeout(() => { copyLinkBtn.textContent = '🔗 Invite'; }, 2000);
    });
});

function connectWebSocket(room, name) {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/${room}/${myUserId}?name=${encodeURIComponent(name)}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        joinScreen.classList.add('hidden');
        gameScreen.classList.remove('hidden');
        document.getElementById('display-room-id').textContent = room;
        document.getElementById('display-username').textContent = `${name} (#${myUserId.split('-')[0]})`;
        renderVotingCards();
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'state_update') {
            roomState = data.state;
            updateUI();
        }
    };

    ws.onclose = () => {
        alert('Disconnected from server. Please refresh.');
        joinScreen.classList.remove('hidden');
        gameScreen.classList.add('hidden');
    };
}

function sendAction(actionObj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(actionObj));
    }
}

function updateUI() {
    // 1. Host controls
    const me = roomState.participants.find(p => p.user_id === roomState.my_user_id);
    const hostControls = document.getElementById('host-controls');
    const revealBtn = document.getElementById('reveal-btn');

    if (me && me.is_host) {
        hostControls.classList.remove('hidden');
        if (roomState.revealed) {
            revealBtn.textContent = 'Hide Cards';
        } else {
            revealBtn.textContent = 'Reveal Cards';
        }

        if (roomState.jira_enabled) {
            jiraControls.classList.remove('hidden');
            if (roomState.revealed && roomState.jira_issue) {
                jiraPushControls.classList.remove('hidden');
            } else {
                jiraPushControls.classList.add('hidden');
            }
        }
    } else {
        hostControls.classList.add('hidden');
    }

    // Jira Banner
    if (roomState.jira_issue) {
        jiraBanner.classList.remove('hidden');
        jiraSummary.textContent = `${roomState.jira_issue.key}: ${roomState.jira_issue.summary}`;
        jiraDescription.textContent = roomState.jira_issue.description || 'No description provided.';
    } else {
        jiraBanner.classList.add('hidden');
    }

    // 2. Game Status
    const gameStatus = document.getElementById('game-status');
    if (roomState.revealed) {
        gameStatus.textContent = "Cards Revealed!";
        gameStatus.style.color = "var(--accent)";
    } else {
        const total = roomState.participants.length;
        const voted = roomState.participants.filter(p => p.has_voted).length;
        gameStatus.textContent = `${voted} / ${total} Voted`;
        gameStatus.style.color = "var(--text-muted)";
    }

    // 3. Update my vote state based on server state (in case of reconnect)
    if (me && me.vote === null) {
        myVote = null;
        document.querySelectorAll('.vote-card').forEach(c => c.classList.remove('selected'));
    } else if (me && me.vote) {
        myVote = me.vote;
        document.querySelectorAll('.vote-card').forEach(c => {
            if (c.textContent === myVote) c.classList.add('selected');
            else c.classList.remove('selected');
        });
    }

    // Disable cards if revealed
    document.getElementById('voting-cards').style.pointerEvents = roomState.revealed ? 'none' : 'auto';
    document.getElementById('voting-cards').style.opacity = roomState.revealed ? '0.5' : '1';

    // 4. Render participants
    const participantsList = document.getElementById('participants-list');
    participantsList.innerHTML = '';

    roomState.participants.forEach(p => {
        const el = document.createElement('div');
        el.className = `participant ${!p.connected ? 'offline' : ''}`;

        const cardEl = document.createElement('div');
        cardEl.className = 'p-card';
        if (p.has_voted) {
            if (roomState.revealed) {
                cardEl.classList.add('revealed');
                cardEl.textContent = p.vote;
            } else {
                cardEl.classList.add('voted');
                cardEl.textContent = '✓';
            }
        } else {
            cardEl.textContent = '...';
        }

        const nameEl = document.createElement('div');
        nameEl.className = 'p-name';
        nameEl.textContent = `${p.name} (#${p.user_id.split('-')[0]})` + (p.user_id === roomState.my_user_id ? ' (You)' : '') + (p.is_host ? ' 👑' : '');

        el.appendChild(cardEl);
        el.appendChild(nameEl);
        participantsList.appendChild(el);
    });
}

function renderVotingCards() {
    const container = document.getElementById('voting-cards');
    container.innerHTML = '';

    VOTE_VALUES.forEach(val => {
        const btn = document.createElement('button');
        btn.className = 'vote-card';
        btn.textContent = val;
        btn.addEventListener('click', () => {
            if (roomState && roomState.revealed) return;
            myVote = val;

            // Visual feedback
            document.querySelectorAll('.vote-card').forEach(c => c.classList.remove('selected'));
            btn.classList.add('selected');

            sendAction({ action: 'vote', value: val });
        });
        container.appendChild(btn);
    });
}

// Host actions
document.getElementById('reveal-btn').addEventListener('click', () => {
    if (roomState && roomState.revealed) {
        sendAction({ action: 'hide' });
    } else {
        sendAction({ action: 'reveal' });
    }
});

document.getElementById('reset-btn').addEventListener('click', () => {
    sendAction({ action: 'reset' });
});

fetchJiraBtn.addEventListener('click', () => {
    const key = jiraKeyInput.value.trim();
    if (key) {
        sendAction({ action: 'fetch_jira_issue', issue_key: key });
    }
});

pushJiraBtn.addEventListener('click', () => {
    const points = jiraPointsInput.value.trim();
    if (points) {
        sendAction({ action: 'push_jira_points', points: points });
        alert(`Instructed backend to push ${points} points to Jira!`);
    }
});
