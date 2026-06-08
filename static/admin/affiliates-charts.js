(function () {
  if (typeof affChartData === 'undefined') return;

  const clicksCtx = document.getElementById('clicksChart');
  if (clicksCtx && affChartData.dailyClicks.length) {
    new Chart(clicksCtx, {
      type: 'bar',
      data: {
        labels: affChartData.dailyClicks.map((d) => d.day.slice(5)),
        datasets: [{
          label: 'Clics affiliés',
          data: affChartData.dailyClicks.map((d) => d.clicks),
          backgroundColor: 'rgba(196, 160, 83, 0.75)',
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#7A7772' } },
          y: { beginAtZero: true, grid: { color: '#F0EBE3' }, ticks: { color: '#7A7772', stepSize: 1 } },
        },
      },
    });
  }

  const partnerCtx = document.getElementById('partnerChart');
  if (partnerCtx && affChartData.partners.length) {
    new Chart(partnerCtx, {
      type: 'doughnut',
      data: {
        labels: affChartData.partners.map((p) => p.name),
        datasets: [{
          data: affChartData.partners.map((p) => p.clicks),
          backgroundColor: ['#1B4D4A', '#2A6B66', '#3D6B5E', '#C4A053', '#C4654A', '#0F3330', '#D4B86A', '#E8D5C4'],
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
      },
    });
  }
})();
