const socket = io(); // Connects to the server

function deployExperiment(uuid) {
    fetch('/api/exp/deploy/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({uuid: uuid})
    })
        .then(response => response.json())
        .then(data => alert(`Status: ${data.status}, Message: ${data.message}`))
        .catch(error => console.error('Error:', error));
}

socket.on('connect', () => {
    console.log('Experiment ID:', experimentId); // Access the experiment ID
    socket.emit('join_room', experimentId); // Use the experiment ID to join a specific room
});

// Handling incoming messages
socket.on('deploy_event', function (data) {
    const messageContainer = document.getElementById('messages');

    const msgElement = document.createElement('div');
    msgElement.classList.add('message');
    msgElement.style.backgroundColor = data.color;
    msgElement.innerText = data.msg; // Assuming data.msg is always text

    messageContainer.appendChild(msgElement);
});

// Optionally handle different types of data like files
socket.on('file_event', function (data) {
    const messageContainer = document.getElementById('messages');

    const fileLink = document.createElement('a');
    fileLink.href = data.url; // URL to download the file
    fileLink.innerText = 'Download File';
    fileLink.style.color = data.color; // Color the link instead of background
    fileLink.classList.add('message');

    messageContainer.appendChild(fileLink);
});
