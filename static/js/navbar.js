document.addEventListener('DOMContentLoaded', () => {
    const syncLink = document.getElementById('sync-link');

    if (syncLink) {
        syncLink.addEventListener('click', function (event) {
            event.preventDefault();

            const message = "This will look for missing media for all posts. Proceed?";
            const userConfirmed = window.confirm(message);

            if (userConfirmed) {
                window.location.href = this.href;
            } else {
                console.log("Sync aborted by user.");
            }
        });
    }
});