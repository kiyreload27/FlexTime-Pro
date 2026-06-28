/* FlexTime Pro — Chart.js Configurations */

const isDark = () => document.documentElement.classList.contains('dark');

const chartColors = {
    indigo: { bg: 'rgba(99, 102, 241, 0.7)', border: 'rgb(99, 102, 241)' },
    violet: { bg: 'rgba(139, 92, 246, 0.7)', border: 'rgb(139, 92, 246)' },
    emerald: { bg: 'rgba(16, 185, 129, 0.5)', border: 'rgb(16, 185, 129)' },
    red: { bg: 'rgba(239, 68, 68, 0.5)', border: 'rgb(239, 68, 68)' },
    amber: { bg: 'rgba(245, 158, 11, 0.5)', border: 'rgb(245, 158, 11)' },
    slate: { bg: 'rgba(148, 163, 184, 0.3)', border: 'rgb(148, 163, 184)' },
};

function getGridColor() {
    return isDark() ? 'rgba(148, 163, 184, 0.1)' : 'rgba(148, 163, 184, 0.2)';
}

function getTextColor() {
    return isDark() ? '#94a3b8' : '#64748b';
}

const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: isDark() ? '#1e293b' : '#0f172a',
            titleColor: '#f8fafc',
            bodyColor: '#e2e8f0',
            cornerRadius: 8,
            padding: 12,
            titleFont: { family: 'Inter', weight: '600' },
            bodyFont: { family: 'Inter' },
        },
    },
    scales: {
        x: {
            grid: { color: getGridColor(), drawBorder: false },
            ticks: { color: getTextColor(), font: { family: 'Inter', size: 11 } },
        },
        y: {
            grid: { color: getGridColor(), drawBorder: false },
            ticks: { color: getTextColor(), font: { family: 'Inter', size: 11 } },
            beginAtZero: true,
        },
    },
};

function initWeeklyChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Hours Worked',
                    data: data.hours,
                    backgroundColor: data.hours.map((h, i) =>
                        h >= (data.targets[i] || 40) ? chartColors.emerald.bg : chartColors.indigo.bg
                    ),
                    borderColor: data.hours.map((h, i) =>
                        h >= (data.targets[i] || 40) ? chartColors.emerald.border : chartColors.indigo.border
                    ),
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Target',
                    data: data.targets,
                    type: 'line',
                    borderColor: chartColors.slate.border,
                    borderDash: [6, 4],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                },
            ],
        },
        options: {
            ...baseOptions,
            plugins: {
                ...baseOptions.plugins,
                legend: { display: true, position: 'top', labels: { color: getTextColor(), font: { family: 'Inter', size: 11 }, usePointStyle: true, pointStyle: 'rectRounded' } },
            },
        },
    });
}

function initMonthlyChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const gradient = ctx.getContext('2d');
    const bg = gradient.createLinearGradient(0, 0, 0, 200);
    bg.addColorStop(0, 'rgba(139, 92, 246, 0.6)');
    bg.addColorStop(1, 'rgba(99, 102, 241, 0.3)');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Monthly Hours',
                data: data.hours,
                backgroundColor: bg,
                borderColor: chartColors.violet.border,
                borderWidth: 2,
                borderRadius: 6,
                borderSkipped: false,
            }],
        },
        options: baseOptions,
    });
}

function initBalanceChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 200);
    const isPositive = data.balances[data.balances.length - 1] >= 0;
    if (isPositive) {
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0.02)');
    } else {
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0.02)');
    }

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Flexitime Balance',
                data: data.balances,
                borderColor: isPositive ? chartColors.emerald.border : chartColors.red.border,
                borderWidth: 2.5,
                backgroundColor: gradient,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: isPositive ? chartColors.emerald.border : chartColors.red.border,
                pointBorderColor: isDark() ? '#0f172a' : '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
            }],
        },
        options: {
            ...baseOptions,
            scales: {
                ...baseOptions.scales,
                y: {
                    ...baseOptions.scales.y,
                    beginAtZero: false,
                },
            },
        },
    });
}
