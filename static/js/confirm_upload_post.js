const tagsInput = document.querySelector('.tags-input-bar__input');
const suggestionsContainer = document.createElement('div');
suggestionsContainer.classList.add('tags-input-bar__search-suggestions');
tagsInput.parentNode.appendChild(suggestionsContainer);
const tagsContainer = document.querySelector('.tags-container');
const saveButton = document.querySelector('.btn--primary');

let allTopics = [];
let tags = [];

function toggleTagsContainer() {
    if (tags.length > 0) {
        tagsContainer.classList.remove('hidden');
    } else {
        tagsContainer.classList.add('hidden');
    }
}

async function fetchAllTopics() {
    try {
        const response = await fetch('/api/topics');
        allTopics = await response.json();
    } catch (err) {
        console.error("Error fetching topics:", err);
    }
}

function getSuggestions(query) {
    const queryLower = query.toLowerCase();
    return allTopics.filter(topic => topic.name.toLowerCase().includes(queryLower) && !tags.includes(topic.name));
}

function renderTags() {
    tagsContainer.innerHTML = '';
    tags.forEach(tag => {
        const tagElement = document.createElement('div');
        tagElement.classList.add('tag');
        tagElement.innerHTML = `
            <span>${tag}</span>
            <button type="button" class="tag__remove-btn" data-tag="${tag}">&times;</button>
        `;
        tagsContainer.appendChild(tagElement);
    });

    document.querySelectorAll('.tag__remove-btn').forEach(button => {
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

    const formattedTag = tag.charAt(0).toUpperCase() + tag.slice(1).toLowerCase();

    if (!tags.includes(formattedTag)) {
        tags.push(formattedTag);
        renderTags();
    }

    tagsInput.value = '';
    suggestionsContainer.innerHTML = '';
}

function displaySuggestions(suggestions) {
    suggestionsContainer.innerHTML = '';
    suggestions.forEach(suggestion => {
        const suggestionElement = document.createElement('div');
        suggestionElement.classList.add('suggestion-item', 'suggestion-item--topic', 'nulled-link', 'hoverable-white');
        suggestionElement.textContent = suggestion.name;
        suggestionElement.addEventListener('click', () => {
            addTag(suggestion.name);
        });
        suggestionsContainer.appendChild(suggestionElement);
    });
}

tagsInput.addEventListener('input', () => {
    const query = tagsInput.value.trim();
    if (query) {
        const suggestions = getSuggestions(query);
        displaySuggestions(suggestions);
    } else {
        suggestionsContainer.innerHTML = '';
    }
});

tagsInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        addTag(tagsInput.value.trim());
    }
});
saveButton.addEventListener('click', async () => {
    if (tags.length === 0) {
        alert('Please add at least one tag.');
        return;
    }

    const data = {
        post_data: postData,
        tags: tags
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

fetchAllTopics();
toggleTagsContainer();
