const reader = new FileReader();
reader.addEventListener('loadend', (e) => {
  const text = e.srcElement.result;
  console.log(text);
});
var ws = new WebSocket('ws://' + document.domain + ':' + location.port + '/ws');
//var ws = new WebSocket('ws://' + document.domain + ':' + location.port + '/api/v2/ws');
ws.onmessage = function (event) {
  console.log("Incoming ws: " + event.data);
  var incoming = JSON.parse(event.data);
  if (incoming.Type == "Chat"){ // handle chat messages
    var messages_dom = document.getElementsByTagName('ul')[0];
    var message_dom = document.createElement('li');
    var content_dom = document.createTextNode('Received: ' + incoming.Data);
    message_dom.appendChild(content_dom);
    messages_dom.appendChild(message_dom);
  }
  if (incoming.Type == "Pixel"){ // handle incoming pixel changes
    var cells = document.getElementsByClassName("cell");
    console.log("Trying to change a pixel; incoming.Data looks like " + incoming.Data);
    // Data looks like "[1, 2, 255, 0, 0]" for "[x, y, r, g, b]"
    var targetx = incoming.Data[0];
    var targety = incoming.Data[1];
    var targetr = incoming.Data[2];
    var targetg = incoming.Data[3];
    var targetb = incoming.Data[4];
    var targetcolor = "rgb(" + targetr + ', ' + targetg + ', ' + targetb + ")" // e.g. "rgb(255, 0, 0)"
    console.log("X is "+targetx+", Y is "+targety+", and color = "+targetcolor)
    for (i = 0; i < cells.length; i++) {
      // console.log("i is " + i + ", and incoming.Data[0] is " + incoming.Data[0] + " and cells[i].dataset.x is " + cells[i].dataset.x)
      if (targetx == cells[i].dataset.x && targety == cells[i].dataset.y) {
        cells[i].style.backgroundColor = targetcolor;
      }
    }
  }
  if (incoming.Type == "System") { //handles system messages
    console.log("Received system message: " + incoming.Data);
  }
};
var button = document.getElementById('sendButton');
button.onclick = function() {
  var content = document.getElementById('chatInput').value;
  ws.send('{"Type":"Chat","Data":"' + content + '"}');
};
function clickCell(cell) { // change a cell's color when clicked
  var r = document.getElementById('redBox').value
  var g = document.getElementById('greenBox').value
  var b = document.getElementById('blueBox').value
  var color = r+", "+g+", "+b
  // cell.style.backgroundColor = color; // change cell color on page
  console.log("Setting cell " + cell.dataset.x + ", " + cell.dataset.y + " to " + color); // log change to console
  ws.send('{"Type":"Pixel","Data":[' + cell.dataset.x + ', ' + cell.dataset.y + ', ' + r+', '+g+', '+b + ']}') // ws message back to server to change cell in device
  return;
}
function brushClick(brush) { // change the brush color when clicked
  brushes = document.getElementsByClassName("brush");
  for (var i = 0; i < brushes.length; i++) {
    // console.log("Current brushes["+i+"].dataset.active == " + brushes[i].dataset.active);
    brushes[i].dataset.active = "False";
  }
  brush.dataset.active = "True";
  console.log("The " + brush.style.backgroundColor + " brush is now active")
  colorBlob = brush.style.backgroundColor.split('(')[1].split(')')[0].split(',') // like [255, 0, 0]
  document.getElementById("redBox").value = colorBlob[0]
  document.getElementById("greenBox").value = colorBlob[1]
  document.getElementById("blueBox").value = colorBlob[2]
}
var animationName = "anim1";
function goLeft() { // go one frame earlier
  var currentFrame = document.getElementById("frameNum").value;
  if (currentFrame != 0) {
    currentFrame = currentFrame - 1;
  }
  document.getElementById("frameNum").value = currentFrame;
}
function goRight() { // go one frame later
  var currentFrame = document.getElementById("frameNum").value;
  currentFrame = currentFrame + 1;
  document.getElementById("frameNum").value = currentFrame;
}
function loadFrame() { // load whatever's in the DB for this frame number into the pixels
  var currentFrame = document.getElementById("frameNum").value;
  ws.send('{"Type":"LoadFrame","Data":[' + animationName + ', ' + currentFrame + ']}') // ws to server to overwrite current state with DB frame
}
function saveFrame() { // save current pixels to frame shown in box
  var currentFrame = document.getElementById("frameNum").value;
  ws.send('{"Type":"SaveFrame","Data":[' + animationName + ', ' + currentFrame + ']}') // ws to server to save current frame
}
function animate() { // animate given current set of frames
  ws.send('{"Type":"Animate","Data":[' + animationName + ', ' + currentFrame + ']}') // ws to request animation
}
console.log("Asking for initial board setup");
ws.onopen = function (event) {
  ws.send('{"Type":"Update"}'); // ws message back to server to get initial state of board    
}