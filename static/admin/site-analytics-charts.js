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
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', maxTicksLimit: 12 } },
          y: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772' } },
        },
      },
    });
  }

  const countries = siteAnalyticsData.countries || [];
  const cities = siteAnalyticsData.cities || [];
  const countryColors = ['#1B4D4A', '#C17F3A', '#2A6F6B', '#8B6914', '#4A7C59', '#6B5B95', '#A0522D', '#4682B4', '#5F7A61', '#9B6B4F'];

  function cityChartLabel(c) {
    if (c.city === 'Inconnu') return c.country_name !== 'Inconnu' ? c.country_name : 'Inconnu';
    if (c.country_code && c.country_code !== '??') return `${c.city} · ${c.country_code}`;
    return c.city;
  }

  const countriesCtx = document.getElementById('countriesChart');
  if (countriesCtx && countries.length) {
    new Chart(countriesCtx, {
      type: 'bar',
      data: {
        labels: countries.map((c) => (c.country_code !== '??' ? `${c.country_code} · ${c.country_name}` : c.country_name)),
        datasets: [{
          label: 'Pages vues',
          data: countries.map((c) => c.views),
          backgroundColor: countryColors,
          borderRadius: 4,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', precision: 0 } },
          y: { grid: { display: false }, ticks: { color: '#7A7772', font: { size: 11 } } },
        },
      },
    });
  }

  const citiesCtx = document.getElementById('citiesChart');
  if (citiesCtx && cities.length) {
    new Chart(citiesCtx, {
      type: 'bar',
      data: {
        labels: cities.map(cityChartLabel),
        datasets: [{
          label: 'Pages vues',
          data: cities.map((c) => c.views),
          backgroundColor: countryColors.slice().reverse(),
          borderRadius: 4,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', precision: 0 } },
          y: { grid: { display: false }, ticks: { color: '#7A7772', font: { size: 11 } } },
        },
      },
    });
  }

  const seo = siteAnalyticsData.seo || {};
  const seoColors = ['#C4A053', '#1B4D4A', '#2A6F6B', '#C4654A', '#7A7772'];

  const seoChannelsCtx = document.getElementById('seoChannelsChart');
  if (seoChannelsCtx && seo.channels_chart && seo.channels_chart.length) {
    new Chart(seoChannelsCtx, {
      type: 'doughnut',
      data: {
        labels: seo.channels_chart.map((s) => s.label),
        datasets: [{
          data: seo.channels_chart.map((s) => s.views),
          backgroundColor: seoColors,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#7A7772', boxWidth: 12 } },
        },
      },
    });
  }

  const seoEnginesCtx = document.getElementById('seoEnginesChart');
  if (seoEnginesCtx && seo.engines_chart && seo.engines_chart.length) {
    new Chart(seoEnginesCtx, {
      type: 'bar',
      data: {
        labels: seo.engines_chart.map((s) => s.label),
        datasets: [{
          label: 'Visites',
          data: seo.engines_chart.map((s) => s.views),
          backgroundColor: '#C4A053',
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#7A7772' } },
          y: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', precision: 0 } },
        },
      },
    });
  }

  const seoDailyCtx = document.getElementById('seoDailyChart');
  if (seoDailyCtx && seo.daily_organic && seo.daily_organic.length) {
    new Chart(seoDailyCtx, {
      type: 'line',
      data: {
        labels: seo.daily_organic.map((d) => d.day.slice(5)),
        datasets: [{
          label: 'Visites SEO',
          data: seo.daily_organic.map((d) => d.views),
          borderColor: '#C4A053',
          backgroundColor: 'rgba(196, 160, 83, 0.12)',
          fill: true,
          tension: 0.35,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', maxTicksLimit: 14 } },
          y: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', precision: 0 } },
        },
      },
    });
  }

  const seoContentCtx = document.getElementById('seoContentChart');
  if (seoContentCtx && seo.content_organic && seo.content_organic.length) {
    new Chart(seoContentCtx, {
      type: 'doughnut',
      data: {
        labels: seo.content_organic.map((s) => s.label),
        datasets: [{
          data: seo.content_organic.map((s) => s.views),
          backgroundColor: ['#1B4D4A', '#C4A053', '#2A6F6B', '#C4654A', '#6B5B95', '#8B6914'],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#7A7772', boxWidth: 12, font: { size: 11 } } },
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
        maintainAspectRatio: false,
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
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#7A7772', maxTicksLimit: 14 } },
          y: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', precision: 0 } },
        },
      },
    });
  }

  // ── Realtime timeline (GA4-style sparkline) ─────────
  let realtimeTimelineChart = null;
  const timelineCtx = document.getElementById('realtimeTimelineChart');

  function timelineBarColor(ctx) {
    const total = ctx.chart.data.datasets[0].data.length;
    const opacity = 0.18 + (ctx.dataIndex / (total - 1)) * 0.67;
    return `rgba(27, 77, 74, ${opacity.toFixed(2)})`;
  }

  if (timelineCtx) {
    realtimeTimelineChart = new Chart(timelineCtx, {
      type: 'bar',
      data: {
        labels: [],
        datasets: [{
          label: 'Pages vues',
          data: [],
          backgroundColor: timelineBarColor,
          borderRadius: 2,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => items[0].label,
              label: (item) => `${item.raw} vue${item.raw !== 1 ? 's' : ''}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#7A7772', maxTicksLimit: 10, font: { size: 10 } },
          },
          y: {
            beginAtZero: true,
            grid: { color: '#F0EBE3' },
            ticks: { color: '#7A7772', precision: 0, font: { size: 10 }, maxTicksLimit: 5 },
          },
        },
      },
    });

    function updateTimeline() {
      fetch('/admin/api/realtime-timeline')
        .then((r) => r.json())
        .then((data) => {
          if (!realtimeTimelineChart) return;
          realtimeTimelineChart.data.labels = data.map((d) => d.minute);
          realtimeTimelineChart.data.datasets[0].data = data.map((d) => d.views);
          realtimeTimelineChart.update('none');
        })
        .catch(() => {});
    }

    updateTimeline();
    setInterval(updateTimeline, 60000);
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
          feed.innerHTML = d.recent.slice(0, 12).map((v) => {
            let loc = '';
            if (v.city && v.city !== 'Inconnu') {
              loc = `<span class="top-pages-list__loc">${v.city}${v.country_code && v.country_code !== '??' ? ` · ${v.country_code}` : ''}</span> `;
            } else if (v.country_code && v.country_code !== '??') {
              loc = `<span class="top-pages-list__country">${v.country_code}</span> `;
            }
            return `<li><span class="top-pages-list__path">${loc}${v.path}</span><span class="top-pages-list__count">${v.created_at.slice(11, 16)}</span></li>`;
          }).join('') || '<li class="muted">En attente de visites…</li>';
        }
      })
      .catch(() => {});
  }, 10000);
})();
