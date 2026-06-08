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

  const geo = siteAnalyticsData.geo || {};
  const geoColors = ['#1B4D4A', '#C17F3A', '#2A6F6B', '#8B6914', '#4A7C59', '#6B5B95', '#A0522D', '#4682B4'];

  const geoSourcesCtx = document.getElementById('geoSourcesChart');
  if (geoSourcesCtx && geo.sources_chart && geo.sources_chart.length) {
    new Chart(geoSourcesCtx, {
      type: 'doughnut',
      data: {
        labels: geo.sources_chart.map((s) => s.label),
        datasets: [{
          data: geo.sources_chart.map((s) => s.views),
          backgroundColor: geoColors,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#7A7772', boxWidth: 12 } },
        },
      },
    });
  }

  const geoDailyCtx = document.getElementById('geoDailyChart');
  if (geoDailyCtx && geo.daily_ai && geo.daily_ai.length) {
    new Chart(geoDailyCtx, {
      type: 'bar',
      data: {
        labels: geo.daily_ai.map((d) => d.day.slice(5)),
        datasets: [{
          label: 'Vues IA',
          data: geo.daily_ai.map((d) => d.total),
          backgroundColor: 'rgba(27, 77, 74, 0.75)',
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#7A7772', maxTicksLimit: 14 } },
          y: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', precision: 0 } },
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
