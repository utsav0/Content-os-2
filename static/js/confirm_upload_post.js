// --- Generic Tag Input System ---
function createTagInput({ inputEl, containerEl, fetchUrl, suggestionClass, formatTag }) {
    const suggestionsContainer = document.createElement('div');
    suggestionsContainer.classList.add('tags-input-bar__search-suggestions');
    inputEl.parentNode.appendChild(suggestionsContainer);

    let allItems = [];
    let tags = [];

    function toggleTagsContainer() {
        if (tags.length > 0) {
            containerEl.classList.remove('hidden');
        } else {
            containerEl.classList.add('hidden');
        }
    }

    async function fetchAllItems() {
        try {
            const response = await fetch(fetchUrl);
            allItems = await response.json();
        } catch (err) {
            console.error(`Error fetching from ${fetchUrl}:`, err);
        }
    }

    function getSuggestions(query) {
        const queryLower = query.toLowerCase();
        return allItems.filter(item => item.name.toLowerCase().includes(queryLower) && !tags.includes(item.name));
    }

    function renderTags() {
        containerEl.innerHTML = '';
        tags.forEach(tag => {
            const tagElement = document.createElement('div');
            tagElement.classList.add('tag');
            tagElement.innerHTML = `
                <span>${tag}</span>
                <button type="button" class="tag__remove-btn" data-tag="${tag}">&times;</button>
            `;
            containerEl.appendChild(tagElement);
        });

        containerEl.querySelectorAll('.tag__remove-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const tagToRemove = e.target.getAttribute('data-tag');
                tags = tags.filter(tag => tag !== tagToRemove);
                renderTags();
                toggleTagsContainer();
            });
        });
        toggleTagsContainer();
    }

    function addTag(tag) {
        if (!tag) return;

        const formattedTag = formatTag ? formatTag(tag) : tag.charAt(0).toUpperCase() + tag.slice(1).toLowerCase();

        if (!tags.includes(formattedTag)) {
            tags.push(formattedTag);
            renderTags();
        }

        inputEl.value = '';
        suggestionsContainer.innerHTML = '';
    }

    function displaySuggestions(suggestions) {
        suggestionsContainer.innerHTML = '';
        suggestions.forEach(suggestion => {
            const suggestionElement = document.createElement('div');
            suggestionElement.classList.add('suggestion-item', suggestionClass, 'nulled-link', 'hoverable-white');
            suggestionElement.textContent = suggestion.name;
            suggestionElement.addEventListener('click', () => {
                addTag(suggestion.name);
            });
            suggestionsContainer.appendChild(suggestionElement);
        });
    }

    inputEl.addEventListener('input', () => {
        const query = inputEl.value.trim();
        if (query) {
            const suggestions = getSuggestions(query);
            displaySuggestions(suggestions);
        } else {
            suggestionsContainer.innerHTML = '';
        }
    });

    inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTag(inputEl.value.trim());
        }
    });

    fetchAllItems();
    toggleTagsContainer();

    return {
        getTags: () => tags,
    };
}

// --- Initialize both tag inputs ---
const topicTagInput = createTagInput({
    inputEl: document.getElementById('topic-tags-input'),
    containerEl: document.getElementById('topic-tags-container'),
    fetchUrl: '/api/topics',
    suggestionClass: 'suggestion-item--topic',
    formatTag: (tag) => tag.charAt(0).toUpperCase() + tag.slice(1).toLowerCase(),
});

const graphicDescTagInput = createTagInput({
    inputEl: document.getElementById('graphic-desc-tags-input'),
    containerEl: document.getElementById('graphic-desc-tags-container'),
    fetchUrl: '/api/graphic-descs',
    suggestionClass: 'suggestion-item--graphic-desc',
    formatTag: (tag) => tag.charAt(0).toUpperCase() + tag.slice(1).toLowerCase(),
});

// --- Save button ---
const saveButton = document.querySelector('.btn--primary');

saveButton.addEventListener('click', async () => {
    const tags = topicTagInput.getTags();
    const graphicDescs = graphicDescTagInput.getTags();

    if (tags.length === 0) {
        alert('Please add at least one topic tag.');
        return;
    }

    const data = {
        post_data: postData,
        tags: tags,
        graphic_descs: graphicDescs,
    };

    try {
        const response = await fetch('/api/save-post', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            window.location.reload();
        }
        else if (response.status === 409) {
            alert(`Notice: ${result.error}`);
            window.location.reload();
        }
        else {
            alert(`Error: ${result.error}`);
        }
    } catch (err) {
        console.error('Error saving post:', err);
        alert('An error occurred while saving the post.');
    }
});
