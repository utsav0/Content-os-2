document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.add-post-form');
    const submitBtn = form.querySelector('.btn');
    const fileInput = document.getElementById('video-upload');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // 1. Update UI to show processing
        const originalBtnText = submitBtn.textContent;
        submitBtn.textContent = 'Converting...';
        submitBtn.disabled = true;
        submitBtn.style.cursor = 'wait';

        const formData = new FormData(form);

        try {
            const response = await fetch('/video-to-gif', {
                method: 'POST',
                body: formData
            });

            const contentType = response.headers.get('content-type');

            if (response.ok && contentType && contentType.includes('image/gif')) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                
                // 4. Create a temporary link to trigger download
                const a = document.createElement('a');
                a.href = url;
                
                const disposition = response.headers.get('content-disposition');
                let filename = 'converted.gif';
                if (disposition && disposition.indexOf('filename=') !== -1) {
                    const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
                    if (matches != null && matches[1]) { 
                        filename = matches[1].replace(/['"]/g, '');
                    }
                } else if (fileInput.files[0]) {
                    const originalName = fileInput.files[0].name;
                    filename = originalName.replace(/\.[^/.]+$/, "") + ".gif";
                }

                a.download = filename;
                document.body.appendChild(a);
                a.click(); // Trigger download
                a.remove();
                window.URL.revokeObjectURL(url);

                form.reset();
            } else {
                alert("An error occurred during conversion. Please check the file format and try again.");
            }

        } catch (err) {
            console.error(err);
            alert("A network error occurred.");
        } finally {
            submitBtn.textContent = originalBtnText;
            submitBtn.disabled = false;
            submitBtn.style.cursor = 'pointer';
        }
    });
});