document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.add-post-form');
    const submitBtn = form.querySelector('.btn');
    const fileInput = document.getElementById('video-upload');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault(); // Stop standard form submission

        // 1. Update UI to show processing
        const originalBtnText = submitBtn.textContent;
        submitBtn.textContent = 'Converting...';
        submitBtn.disabled = true;
        submitBtn.style.cursor = 'wait';

        const formData = new FormData(form);

        try {
            // 2. Send data via Fetch
            const response = await fetch('/video-to-gif', {
                method: 'POST',
                body: formData
            });

            // Check if the response is the GIF image
            const contentType = response.headers.get('content-type');

            if (response.ok && contentType && contentType.includes('image/gif')) {
                // 3. Create a blob from the response
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                
                // 4. Create a temporary link to trigger download
                const a = document.createElement('a');
                a.href = url;
                
                // Try to get the filename from headers, or fallback to default
                const disposition = response.headers.get('content-disposition');
                let filename = 'converted.gif';
                if (disposition && disposition.indexOf('filename=') !== -1) {
                    const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
                    if (matches != null && matches[1]) { 
                        filename = matches[1].replace(/['"]/g, '');
                    }
                } else if (fileInput.files[0]) {
                    // Fallback: use original name + .gif
                    const originalName = fileInput.files[0].name;
                    filename = originalName.replace(/\.[^/.]+$/, "") + ".gif";
                }

                a.download = filename;
                document.body.appendChild(a);
                a.click(); // Trigger download
                a.remove();
                window.URL.revokeObjectURL(url);

                // 5. RESET THE FORM
                form.reset();
            } else {
                // Handle errors (e.g., if the server returned the HTML error page)
                alert("An error occurred during conversion. Please check the file format and try again.");
            }

        } catch (err) {
            console.error(err);
            alert("A network error occurred.");
        } finally {
            // 6. Restore Button State
            submitBtn.textContent = originalBtnText;
            submitBtn.disabled = false;
            submitBtn.style.cursor = 'pointer';
        }
    });
});