document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("upload-now");
    const status = document.getElementById("status");
  
    btn.addEventListener("click", () => {
      status.textContent = "Uploading history...";
      chrome.runtime.sendMessage({ type: "SEND_HISTORY_NOW" }, (response) => {
        if (chrome.runtime.lastError) {
          status.textContent = "Error: " + chrome.runtime.lastError.message;
          return;
        }
  
        if (response && response.ok) {
          status.textContent = "Upload successful.";
        } else {
          status.textContent = "Upload failed: " + (response && response.error ? response.error : "Unknown error");
        }
      });
    });
  });
  