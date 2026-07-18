let labels = JSON.parse(document.getElementById("chart-labels").textContent);
let costs = JSON.parse(document.getElementById("chart-costs").textContent);

const ctx = document.getElementById('monthlyChart').getContext('2d');
const monthlyChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: {{ labels | tojson }},
        datasets: [{
            label: 'Monthly Cost (₹)',
            data: {{ costs | tojson }},
            backgroundColor: 'rgba(54, 162, 235, 0.7)',
            borderColor: 'rgba(54, 162, 235, 1)',	
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    callback: function(value) {
                        return '₹' + value.toLocaleString();
                    }
                }
            }
        },
        plugins: {
            legend: { display: false }
        }
    }
});