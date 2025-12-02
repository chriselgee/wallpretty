let ws = null;
let isPainting = false;
const paintedCells = new Set();
const coordToCell = new Map();
let savedStates = [];

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

const setSaveStatus = (message, state = 'info') => {
  const status = document.getElementById('saveStatus');
  if (!status) {
    return;
  }
  status.textContent = message || '';
  status.dataset.state = state;
};

const populateSavedStates = (states) => {
  const select = document.getElementById('savedStateSelect');
  if (!select) {
    return;
  }
  const previousValue = select.value;
  select.innerHTML = '';
  if (!states.length) {
    const option = document.createElement('option');
    option.value = '';
    option.disabled = true;
    option.selected = true;
    option.textContent = 'No saved states yet';
    select.appendChild(option);
    return;
  }
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.disabled = true;
  placeholder.selected = !states.some((state) => state.slug === previousValue);
  placeholder.textContent = 'Select a saved state';
  select.appendChild(placeholder);
  states.forEach((state) => {
    const option = document.createElement('option');
    option.value = state.slug;
    option.textContent = state.name || state.slug;
    option.dataset.savedAt = state.saved_at || '';
    select.appendChild(option);
  });
  if (previousValue && states.some((state) => state.slug === previousValue)) {
    select.value = previousValue;
  }
};

const fetchSavedStates = async () => {
  try {
    const response = await fetch('/api/saves');
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      payload = {};
    }
    if (!response.ok) {
      throw new Error(payload.error || 'Unable to load saved states.');
    }
    savedStates = Array.isArray(payload.saves) ? payload.saves : [];
    populateSavedStates(savedStates);
    if (savedStates.length) {
      setSaveStatus(`Loaded ${savedStates.length} saved state${savedStates.length === 1 ? '' : 's'}.`, 'success');
    } else {
      setSaveStatus('No saved states yet.', 'info');
    }
  } catch (error) {
    console.error('Failed to load saved states', error);
    setSaveStatus(error.message || 'Unable to load saved states.', 'error');
  }
};

const handleSaveSnapshot = async () => {
  const input = document.getElementById('saveNameInput');
  if (!input) {
    return;
  }
  const rawName = input.value.trim();
  if (!rawName) {
    setSaveStatus('Enter a name before saving.', 'error');
    input.focus();
    return;
  }
  setSaveStatus('Saving current board...', 'info');
  try {
    const response = await fetch('/api/saves', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name: rawName })
    });
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      payload = {};
    }
    if (!response.ok) {
      throw new Error(payload.error || 'Unable to save board state.');
    }
    input.value = '';
    const savedName = (payload.save && payload.save.name) || rawName;
    setSaveStatus(`Saved "${savedName}" successfully.`, 'success');
    await fetchSavedStates();
    const select = document.getElementById('savedStateSelect');
    if (select && payload.save && payload.save.slug) {
      select.value = payload.save.slug;
    }
  } catch (error) {
    console.error('Failed to save board state', error);
    setSaveStatus(error.message || 'Unable to save board state.', 'error');
  }
};

const applySavedPixels = (pixels) => {
  if (!Array.isArray(pixels)) {
    throw new Error('Saved pixel data is invalid.');
  }
  let updates = 0;
  for (let x = 0; x < pixels.length; x += 1) {
    const column = pixels[x];
    if (!Array.isArray(column)) {
      continue;
    }
    for (let y = 0; y < column.length; y += 1) {
      const triple = column[y];
      if (!Array.isArray(triple) || triple.length < 3) {
        continue;
      }
      const [r, g, b] = triple.map((value) => clampColorValue(value));
      const cell = coordToCell.get(`${x}-${y}`);
      if (cell) {
        cell.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
      }
      safeSend({ Type: 'Pixel', Data: [x, y, r, g, b] });
      updates += 1;
    }
  }
  return updates;
};

const handleLoadSnapshot = async () => {
  const select = document.getElementById('savedStateSelect');
  if (!select) {
    return;
  }
  const slug = select.value;
  if (!slug) {
    setSaveStatus('Select a saved state to load.', 'error');
    return;
  }
  setSaveStatus('Loading saved state...', 'info');
  try {
    const response = await fetch(`/api/saves/${encodeURIComponent(slug)}`);
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      payload = {};
    }
    if (!response.ok) {
      throw new Error(payload.error || 'Unable to load saved state.');
    }
    if (!Array.isArray(payload.pixels)) {
      throw new Error('Saved file is missing pixel data.');
    }
    const updates = applySavedPixels(payload.pixels);
    const label = payload.name || slug;
    setSaveStatus(`Loaded ${label} (${updates} pixels).`, 'success');
  } catch (error) {
    console.error('Failed to load saved state', error);
    setSaveStatus(error.message || 'Unable to load saved state.', 'error');
  }
};

const setupSaveRestore = () => {
  const saveButton = document.getElementById('saveSnapshotButton');
  if (saveButton) {
    saveButton.addEventListener('click', handleSaveSnapshot);
  }
  const loadButton = document.getElementById('loadSnapshotButton');
  if (loadButton) {
    loadButton.addEventListener('click', handleLoadSnapshot);
  }
  const refreshButton = document.getElementById('refreshSavesButton');
  if (refreshButton) {
    refreshButton.addEventListener('click', () => {
      fetchSavedStates();
    });
  }
  const input = document.getElementById('saveNameInput');
  if (input) {
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        handleSaveSnapshot();
      }
    });
  }
  fetchSavedStates();
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
  setupSaveRestore();
  enhanceBrushAccessibility();
  primeDefaultBrush();
  initWebSocket();
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}