(function () {
  if (typeof siteAnalyticsData === 'undefined') return;

  const viewsCtx = document.getElementById('viewsChart');
  if (viewsCtx && siteAnalyticsData.dailyViews.length) {
    new Chart(viewsCtx, {
      type: 'line',
      data: {
        labels: siteAnalyticsData.dailyViews.map((d) => d.day.slice(5)),
        datasets: [{
          label: 'Pages vues',
          data: siteAnalyticsData.dailyViews.map((d) => d.views),
          borderColor: '#1B4D4A',
          backgroundColor: 'rgba(27, 77, 74, 0.08)',
          fill: true,
          tension: 0.35,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', maxTicksLimit: 12 } },
          y: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772' } },
        },
      },
    });
  }

  setInterval(() => {
    fetch('/admin/api/realtime')
      .then((r) => r.json())
      .then((d) => {
        const active = document.getElementById('rt-active');
        const views = document.getElementById('rt-views');
        const clicks = document.getElementById('rt-clicks');
        if (active) active.textContent = d.active_visitors;
        if (views) views.textContent = d.views_30m;
        if (clicks) clicks.textContent = d.clicks_30m;
        const feed = document.getElementById('live-feed');
        if (feed && d.recent) {
          feed.innerHTML = d.recent.slice(0, 12).map((v) =>
            `<li><span class="top-pages-list__path">${v.path}</span><span class="top-pages-list__count">${v.created_at.slice(11, 16)}</span></li>`
          ).join('') || '<li class="muted">En attente de visites…</li>';
        }
      })
      .catch(() => {});
  }, 10000);
})();
