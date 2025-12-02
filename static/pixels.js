let ws = null;
let isPainting = false;
const paintedCells = new Set();
const coordToCell = new Map();
const animationName = "anim1";

const clampColorValue = (value) => {
  const numeric = parseInt(value, 10);
  if (Number.isNaN(numeric)) {
    return 0;
  }
  return Math.min(255, Math.max(0, numeric));
};

const getCurrentColor = () => {
  const rInput = document.getElementById('redBox');
  const gInput = document.getElementById('greenBox');
  const bInput = document.getElementById('blueBox');
  const r = clampColorValue(rInput ? rInput.value : 0);
  const g = clampColorValue(gInput ? gInput.value : 0);
  const b = clampColorValue(bInput ? bInput.value : 0);
  return {
    r,
    g,
    b,
    css: `rgb(${r}, ${g}, ${b})`
  };
};

const keyFromCell = (cell) => {
  if (!cell) {
    return null;
  }
  if (!cell.dataset.coord) {
    cell.dataset.coord = `${cell.dataset.x}-${cell.dataset.y}`;
  }
  return cell.dataset.coord;
};

const safeSend = (payload) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  }
};

function clickCell(cell) {
  if (!cell) {
    return;
  }
  const color = getCurrentColor();
  cell.style.backgroundColor = color.css;
  safeSend({
    Type: 'Pixel',
    Data: [Number(cell.dataset.x), Number(cell.dataset.y), color.r, color.g, color.b]
  });
}

function brushClick(brush) {
  const brushes = document.getElementsByClassName('brush');
  Array.from(brushes).forEach((b) => {
    b.dataset.active = 'False';
  });
  brush.dataset.active = 'True';
  const colorBlob = brush.style.backgroundColor.match(/\d+/g) || ['0', '0', '0'];
  const [r, g, b] = colorBlob.map((value) => clampColorValue(value));
  const redInput = document.getElementById('redBox');
  const greenInput = document.getElementById('greenBox');
  const blueInput = document.getElementById('blueBox');
  if (redInput) redInput.value = r;
  if (greenInput) greenInput.value = g;
  if (blueInput) blueInput.value = b;
}

const appendChat = (message) => {
  const chatLog = document.querySelector('.chat-log');
  if (!chatLog) {
    return;
  }
  const item = document.createElement('li');
  item.textContent = `Received: ${message}`;
  chatLog.appendChild(item);
  chatLog.scrollTop = chatLog.scrollHeight;
};

const handlePixelMessage = (data) => {
  const [x, y, r, g, b] = data;
  const key = `${x}-${y}`;
  const cell = coordToCell.get(key);
  if (cell) {
    cell.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
  }
};

const handleSocketMessage = (event) => {
  let incoming;
  try {
    incoming = JSON.parse(event.data);
  } catch (error) {
    console.error('Failed to parse message', event.data);
    return;
  }
  switch (incoming.Type) {
    case 'Chat':
      appendChat(incoming.Data);
      break;
    case 'Pixel':
      handlePixelMessage(incoming.Data);
      break;
    case 'System':
      console.log('System message:', incoming.Data);
      break;
    default:
      console.log('Unhandled message type:', incoming);
      break;
  }
};

const setupChat = () => {
  const button = document.getElementById('sendButton');
  const input = document.getElementById('chatInput');
  if (!button || !input) {
    return;
  }
  const sendMessage = () => {
    const content = input.value.trim();
    if (!content) {
      return;
    }
    safeSend({ Type: 'Chat', Data: content });
    input.value = '';
  };
  button.addEventListener('click', sendMessage);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      sendMessage();
    }
  });
};

const paintIfNeeded = (cell) => {
  const key = keyFromCell(cell);
  if (!key || paintedCells.has(key)) {
    return;
  }
  paintedCells.add(key);
  clickCell(cell);
};

const handlePointerDown = (event) => {
  if (event.pointerType === 'mouse' && event.button !== 0) {
    return;
  }
  event.preventDefault();
  paintedCells.clear();
  isPainting = true;
  paintIfNeeded(event.currentTarget);
};

const handlePointerEnter = (event) => {
  if (!isPainting) {
    return;
  }
  event.preventDefault();
  paintIfNeeded(event.currentTarget);
};

const stopPainting = () => {
  if (!isPainting) {
    return;
  }
  isPainting = false;
  paintedCells.clear();
};

const handleCellKeyDown = (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    clickCell(event.currentTarget);
  }
};

const setupCells = () => {
  const cells = document.querySelectorAll('.cell');
  cells.forEach((cell) => {
    const key = keyFromCell(cell);
    coordToCell.set(key, cell);
    cell.addEventListener('pointerdown', handlePointerDown);
    cell.addEventListener('pointerenter', handlePointerEnter);
    cell.addEventListener('keydown', handleCellKeyDown);
  });
  window.addEventListener('pointerup', stopPainting);
  window.addEventListener('pointercancel', stopPainting);
  window.addEventListener('pointerleave', stopPainting);
};

const initWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${protocol}://${window.location.host}/ws`;
  ws = new WebSocket(wsUrl);
  ws.addEventListener('message', handleSocketMessage);
  ws.addEventListener('open', () => {
    console.log('Requesting initial board state');
    safeSend({ Type: 'Update' });
  });
  ws.addEventListener('close', () => {
    console.warn('WebSocket connection closed');
  });
};

function goLeft() {
  const frameInput = document.getElementById('frameNum');
  if (!frameInput) {
    return;
  }
  const currentFrame = Math.max(0, (parseInt(frameInput.value, 10) || 0) - 1);
  frameInput.value = currentFrame;
}

function goRight() {
  const frameInput = document.getElementById('frameNum');
  if (!frameInput) {
    return;
  }
  const currentFrame = (parseInt(frameInput.value, 10) || 0) + 1;
  frameInput.value = currentFrame;
}

function loadFrame() {
  const frameInput = document.getElementById('frameNum');
  if (!frameInput) {
    return;
  }
  const currentFrame = parseInt(frameInput.value, 10) || 0;
  safeSend({ Type: 'LoadFrame', Data: [animationName, currentFrame] });
}

function saveFrame() {
  const frameInput = document.getElementById('frameNum');
  if (!frameInput) {
    return;
  }
  const currentFrame = parseInt(frameInput.value, 10) || 0;
  safeSend({ Type: 'SaveFrame', Data: [animationName, currentFrame] });
}

function animate() {
  const frameInput = document.getElementById('frameNum');
  if (!frameInput) {
    return;
  }
  const currentFrame = parseInt(frameInput.value, 10) || 0;
  safeSend({ Type: 'Animate', Data: [animationName, currentFrame] });
}

const enhanceBrushAccessibility = () => {
  const brushes = document.querySelectorAll('.brush');
  brushes.forEach((brush) => {
    brush.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        brushClick(brush);
      }
    });
  });
};

const primeDefaultBrush = () => {
  const current = document.querySelector('.brush[data-active="True"]') || document.querySelector('.brush');
  if (current) {
    brushClick(current);
  }
};

const init = () => {
  setupCells();
  setupChat();
  enhanceBrushAccessibility();
  primeDefaultBrush();
  initWebSocket();
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}