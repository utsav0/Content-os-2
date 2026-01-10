const fileInput = document.getElementById('file-upload');
const fileTagsContainer = document.getElementById('file-tags-container');

let files = [];

fileInput.addEventListener('change', (e) => {
    for (const file of e.target.files) {
        const allowedTypes = ['text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
        if (allowedTypes.includes(file.type) && !files.some(f => f.name === file.name)) {
            files.push(file);
            
        }
    }
    updateFileTags();
    updateFileInput();
});

function updateFileTags() {
    fileTagsContainer.innerHTML = '';
    files.forEach((file, index) => {
        const tag = document.createElement('div');
        tag.classList.add('file-tag');
        tag.innerHTML = `
            <span>${file.name}</span>
            <button type="button" class="remove-file-btn" data-index="${index}">&times;</button>
        `;
        fileTagsContainer.appendChild(tag);
    });

    document.querySelectorAll('.remove-file-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const index = e.target.getAttribute('data-index');
            files.splice(index, 1);
            updateFileTags();
            updateFileInput();
        });
    });
}

function updateFileInput() {
    const dataTransfer = new DataTransfer();
    files.forEach(file => {
        dataTransfer.items.add(file);
    });
    fileInput.files = dataTransfer.files;
}
