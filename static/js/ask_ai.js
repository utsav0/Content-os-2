document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('send-btn');

    function addMessage(content, sender, isHTML = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);
        
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        
        if (isHTML) {
            contentDiv.innerHTML = content;
        } else {
            contentDiv.textContent = content;
        }

        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
    }

    function generateTableHTML(data, sqlQuery) {
        if (!data || data.length === 0) {
            return `<div class="sql-query-display">${sqlQuery}</div><p>No results found for this query.</p>`;
        }

        let html = `<div class="sql-query-display">${sqlQuery}</div>`;
        html += `<table class="ai-data-table"><thead><tr>`;
        
        // Create Headers based on the keys of the first object
        const keys = Object.keys(data[0]);
        keys.forEach(key => {
            html += `<th>${key}</th>`;
        });
        html += `</tr></thead><tbody>`;

        // Create Rows
        data.forEach(row => {
            html += `<tr>`;
            keys.forEach(key => {
                html += `<td>${row[key]}</td>`;
            });
            html += `</tr>`;
        });

        html += `</tbody></table>`;
        return html;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = userInput.value.trim();
        if (!question) return;

        // 1. Show user message
        addMessage(question, 'user');
        userInput.value = '';
        
        // Disable input while loading
        userInput.disabled = true;
        sendBtn.disabled = true;

        // 2. Add temporary loading message
        const loadingId = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('message', 'ai-message');
        loadingDiv.id = loadingId;
        loadingDiv.innerHTML = `<div class="message-content">Thinking... <i class="fa-solid fa-spinner fa-spin"></i></div>`;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            // 3. Call the backend API
            const response = await fetch('/api/ask-ai-query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question })
            });

            const result = await response.json();
            
            // Remove loading message
            document.getElementById(loadingId).remove();

            if (response.ok) {
                // 4. Generate table and show success
                const tableHTML = generateTableHTML(result.data, result.sql);
                addMessage(tableHTML, 'ai', true);
            } else {
                // Show error
                addMessage(`Error: ${result.error}`, 'ai');
            }
        } catch (error) {
            document.getElementById(loadingId).remove();
            addMessage("A network error occurred while connecting to the AI.", 'ai');
            console.error(error);
        } finally {
            // Re-enable input
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });
});