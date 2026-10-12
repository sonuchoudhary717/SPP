// =====================================
// STUDENT PERFORMANCE DISTRIBUTION
// =====================================

document.addEventListener("DOMContentLoaded", function () {
    const labelsElement = document.getElementById("performanceLabelsData");
    const countsElement = document.getElementById("performanceCountsData");
    const canvas = document.getElementById("performanceChart");
    const chartMessage = document.getElementById("chartMessage");
    const chartContainer = document.getElementById("chartContainer");

    if (!labelsElement || !countsElement || !canvas) {
        console.error("Performance chart elements were not found.");
        return;
    }

    let labels = [];
    let counts = [];

    try {
        labels = JSON.parse(labelsElement.textContent || "[]");
        counts = JSON.parse(countsElement.textContent || "[]");
    } catch (error) {
        console.error("Unable to read chart data:", error);
    }

    // Make sure labels and counts are valid and aligned.
    const validData = Array.isArray(labels) &&
        Array.isArray(counts) &&
        labels.length > 0 &&
        labels.length === counts.length;

    if (!validData || typeof Chart === "undefined") {
        canvas.style.display = "none";

        if (chartContainer) {
            chartContainer.style.display = "none";
        }

        if (chartMessage) {
            chartMessage.hidden = false;
            chartMessage.textContent = typeof Chart === "undefined"
                ? "Chart library could not load. Check your internet connection."
                : "No performance data is available yet.";
        }

        console.error("Chart.js or valid performance data is unavailable.");
        return;
    }

    if (chartMessage) {
        chartMessage.hidden = true;
    }

    // Navy blue, blue and light blue theme.
    function getBarColor(label) {
        const category = String(label).toLowerCase();

        if (category.includes("excellent")) {
            return "#142b4a";
        }

        if (category.includes("good")) {
            return "#2563eb";
        }

        if (category.includes("average")) {
            return "#60a5fa";
        }

        if (category.includes("needs improvement")) {
            return "#64748b";
        }

        return "#3b82f6";
    }

    const backgroundColors = labels.map(getBarColor);

    const borderColors = labels.map(function (label) {
        const category = String(label).toLowerCase();

        if (category.includes("excellent")) return "#0f1f35";
        if (category.includes("good")) return "#1d4ed8";
        if (category.includes("average")) return "#3b82f6";

        return "#334155";
    });

    // Create the chart using actual Flask/MySQL data.
    new Chart(canvas, {
        type: "bar",

        data: {
            labels: labels,

            datasets: [{
                label: "Number of Students",
                data: counts,

                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 1,

                borderRadius: 8,
                borderSkipped: false,

                maxBarThickness: 100,
                barPercentage: 0.65,
                categoryPercentage: 0.72
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            animation: {
                duration: 900,
                easing: "easeOutQuart"
            },

            interaction: {
                intersect: false,
                mode: "index"
            },

            plugins: {
                legend: {
                    display: true,
                    position: "top",

                    labels: {
                        color: "#334155",
                        usePointStyle: true,
                        pointStyle: "rectRounded",
                        padding: 20,

                        font: {
                            size: 12,
                            weight: "600"
                        }
                    }
                },

                tooltip: {
                    backgroundColor: "#111827",
                    titleColor: "#ffffff",
                    bodyColor: "#ffffff",
                    padding: 12,
                    cornerRadius: 8,

                    callbacks: {
                        label: function (context) {
                            return " Students: " + context.parsed.y;
                        }
                    }
                }
            },

            scales: {
                x: {
                    grid: {
                        display: false
                    },

                    ticks: {
                        color: "#334155",

                        font: {
                            size: 12,
                            weight: "600"
                        }
                    },

                    border: {
                        display: false
                    }
                },

                y: {
                    beginAtZero: true,

                    ticks: {
                        precision: 0,
                        stepSize: 1,
                        color: "#64748b"
                    },

                    grid: {
                        color: "#e5e7eb",
                        drawTicks: false
                    },

                    border: {
                        display: false
                    }
                }
            }
        }
    });
});