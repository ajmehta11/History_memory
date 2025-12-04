const FUNCTION_URL = "https://ingesthistory-func.azurewebsites.net/api/ingesthistory";

async function sendHistory() {
  return new Promise((resolve, reject) => {
    const ONE_DAY_MS = 24 * 60 * 60 * 1000;
    const startTime = Date.now() - ONE_DAY_MS;

    chrome.history.search(
      {
        text: "",
        maxResults: 1000,
        startTime: startTime
      },
      (items) => {
        console.log(`Retrieved ${items.length} history items. Sending to Azure...`);

        fetch(FUNCTION_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(items)
        })
          .then((res) => {
            if (!res.ok) {
              const msg = `Failed to send history: ${res.status} ${res.statusText}`;
              console.error(msg);
              reject(new Error(msg));
            } else {
              console.log("History sent to Azure successfully.");
              resolve();
            }
          })
          .catch((err) => {
            console.error("Error sending history to Azure:", err);
            reject(err);
          });
      }
    );
  });
}

// Create an hourly alarm when the extension is installed/updated
chrome.runtime.onInstalled.addListener(() => {
  // For testing you can use { periodInMinutes: 1 }
  chrome.alarms.create("sendHistory", { periodInMinutes: 60 });
  console.log("Alarm 'sendHistory' created.");
});

// Automatic cron-like upload
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name !== "sendHistory") return;

  console.log("sendHistory alarm triggered.");
  sendHistory().catch((err) => {
    console.error("Automatic sendHistory failed:", err);
  });
});

// Manual trigger from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "SEND_HISTORY_NOW") {
    console.log("Manual sendHistory requested from popup.");
    sendHistory()
      .then(() => {
        sendResponse({ ok: true });
      })
      .catch((err) => {
        sendResponse({ ok: false, error: String(err) });
      });
    return true; 
  }
});
