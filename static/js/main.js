document.addEventListener("DOMContentLoaded", () => {
    const salesCanvas = document.getElementById("salesChart");
    if (salesCanvas && window.chartLabels) {
        new Chart(salesCanvas, {
            type: "bar",
            data: {
                labels: window.chartLabels,
                datasets: [{
                    label: "Sold Units",
                    data: window.chartValues
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: "#fff" } } },
                scales: {
                    x: { ticks: { color: "#cbd5e1" } },
                    y: { ticks: { color: "#cbd5e1" } }
                }
            }
        });
    }

    const categoryCanvas = document.getElementById("categoryChart");
    if (categoryCanvas && window.categoryLabels) {
        new Chart(categoryCanvas, {
            type: "doughnut",
            data: {
                labels: window.categoryLabels,
                datasets: [{
                    label: "Sales",
                    data: window.categorySales
                }]
            }
        });
    }

    const profitCanvas = document.getElementById("profitChart");
    if (profitCanvas && window.categoryLabels) {
        new Chart(profitCanvas, {
            type: "bar",
            data: {
                labels: window.categoryLabels,
                datasets: [{
                    label: "Profit",
                    data: window.categoryProfit
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: "#fff" } } },
                scales: {
                    x: { ticks: { color: "#cbd5e1" } },
                    y: { ticks: { color: "#cbd5e1" } }
                }
            }
        });
    }
});
