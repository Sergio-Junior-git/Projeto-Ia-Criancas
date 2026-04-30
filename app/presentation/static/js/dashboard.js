const resetButton = document.querySelector("#resetProgress");
const csrfToken = document.querySelector("meta[name='csrf-token']").content;

if (resetButton) {
    resetButton.addEventListener("click", async () => {
        const response = await fetch("/api/reset-progress", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": csrfToken,
            },
        });
        if (response.ok) {
            window.location.reload();
        }
    });
}
