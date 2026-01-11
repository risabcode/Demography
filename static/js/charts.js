// Simple Chart.js setup — page should include Chart.js CDN and a <canvas id="formsChart">
async function loadAdminStats() {
  const res = await fetch('/api/admin/stats');
  const data = await res.json();

  // forms distribution
  const labels = Object.keys(data.forms);
  const values = labels.map(k => data.forms[k] || 0);

  const ctx = document.getElementById('formsChart');
  if (ctx) {
    new Chart(ctx, {
      type: 'pie',
      data: {
        labels: labels,
        datasets: [{
          label: 'Forms',
          data: values
        }]
      }
    });
  }

  // tickets distribution (if canvas)
  const tlabels = Object.keys(data.tickets);
  const tvalues = tlabels.map(k => data.tickets[k] || 0);
  const tctx = document.getElementById('ticketsChart');
  if (tctx) {
    new Chart(tctx, {
      type: 'doughnut',
      data: {
        labels: tlabels,
        datasets: [{
          label: 'Tickets',
          data: tvalues
        }]
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', loadAdminStats);
