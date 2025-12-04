let historyData = [];

chrome.history.search({
  text: '',
  maxResults: 1000,
  startTime: Date.now() - (24 * 60 * 60 * 1000)
}, (historyItems) => {
  historyData = historyItems;
  const historyList = document.getElementById('history-list');

  historyItems.forEach((item) => {
    const li = document.createElement('li');
    const link = document.createElement('a');
    link.href = item.url;
    link.textContent = item.title || item.url;
    link.target = '_blank';
    li.appendChild(link);
    historyList.appendChild(li);
  });
});

document.getElementById('export-btn').addEventListener('click', () => {
  const dataStr = JSON.stringify(historyData, null, 2);
  const blob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'history.json';
  a.click();
  URL.revokeObjectURL(url);
});