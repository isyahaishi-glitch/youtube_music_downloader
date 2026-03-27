document.getElementById('sendBtn').addEventListener('click', async () => {
    const data = document.getElementById('userInput').value;

    // Sending the data to a local Python server
    const response = await fetch('http://127.0.0.1:5000/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: data })
    });

    const result = await response.json();
    console.log("Python says:", result.status);
});