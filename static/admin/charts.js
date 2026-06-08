if (typeof dailyData !== 'undefined' && document.getElementById('viewsChart')) {
  const ctx = document.getElementById('viewsChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dailyData.map(d => d.day),
      datasets: [{
        label: 'Pages vues',
        data: dailyData.map(d => d.views),
        backgroundColor: 'rgba(27, 77, 74, 0.65)',
        borderColor: 'rgba(196, 160, 83, 0.8)',
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#7A7772', maxRotation: 45 }, grid: { color: '#F0EBE3' } },
        y: { ticks: { color: '#7A7772' }, grid: { color: '#F0EBE3' }, beginAtZero: true },
      },
    },
  });
}

setInterval(() => {
  fetch('/admin/api/realtime')
    .then(r => r.json())
    .then(d => {
      const map = { 'rt-active': d.active_visitors, 'rt-views': d.views_30m, 'rt-clicks': d.clicks_30m, 'live-visitors': d.active_visitors };
      Object.entries(map).forEach(([id, val]) => { const el = document.getElementById(id); if (el) el.textContent = val; });
      const feed = document.getElementById('live-feed');
      if (feed && d.recent) {
        feed.innerHTML = d.recent.map(v =>
          `<li><span>${v.path}</span><time>${v.created_at.slice(11, 16)}</time></li>`
        ).join('');
      }
    })
    .catch(() => {});
}, 10000);
