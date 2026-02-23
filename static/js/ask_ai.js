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
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function generateTableHTML(data, sqlQuery) {
        if (!data || data.length === 0) {
            return `<div class="sql-query-display">${sqlQuery}</div><p>No results found for this query.</p>`;
        }

        let html = `<div class="sql-query-display">${sqlQuery}</div>`;
        html += `<table class="ai-data-table"><thead><tr>`;

        const keys = Object.keys(data[0]);
        keys.forEach(key => {
            html += `<th>${key}</th>`;
        });
        html += `</tr></thead><tbody>`;
        // Create Rows
        data.forEach(row => {
            html += `<tr>`;
            keys.forEach(key => {
                let cellValue = row[key];

                // 1. Truncate the caption if it's longer than 70 characters
                if (key === 'caption' && typeof cellValue === 'string' && cellValue.length > 70) {
                    cellValue = cellValue.substring(0, 70) + '...';
                }

                // 2. Handle null values gracefully
                if (cellValue === null) {
                    cellValue = '-';
                }

                // 3. Make the post_id column a clickable link
                if (key === 'post_id' && cellValue !== '-') {
                    cellValue = `<a href="/post/${cellValue}" target="_blank" style="color: var(--clr-accent); text-decoration: none; font-weight: 600;">${cellValue}</a>`;
                }

                // 4. If rendering the caption AND the AI also fetched the post_id, make the caption clickable too!
                if (key === 'caption' && row['post_id'] && cellValue !== '-') {
                    cellValue = `<a href="/post/${row['post_id']}" target="_blank" style="color: var(--clr-accent); text-decoration: none;">${cellValue}</a>`;
                }

                html += `<td>${cellValue}</td>`;
            });
            html += `</tr>`;
        });

        html += `</tbody></table>`;
        return html;
    }

    function buildResponseHTML(result) {
        let html = '';

        if (result.analysis) {
            html += `<div class="ai-analysis">${result.analysis}</div>`;
        }

        html += generateTableHTML(result.data, result.sql);
        return html;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = userInput.value.trim();
        if (!question) return;

        addMessage(question, 'user');
        userInput.value = '';

        userInput.disabled = true;
        sendBtn.disabled = true;

        const loadingId = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('message', 'ai-message');
        loadingDiv.id = loadingId;
        loadingDiv.innerHTML = `<div class="message-content">Thinking... <i class="fa-solid fa-spinner fa-spin"></i></div>`;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/api/ask-ai-query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question })
            });

            const result = await response.json();

            document.getElementById(loadingId).remove();

            if (response.ok) {
                const responseHTML = buildResponseHTML(result);
                addMessage(responseHTML, 'ai', true);
            } else {
                addMessage(`Error: ${result.error}`, 'ai');
            }
        } catch (error) {
            document.getElementById(loadingId).remove();
            addMessage("A network error occurred while connecting to the AI.", 'ai');
            console.error(error);
        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });
});