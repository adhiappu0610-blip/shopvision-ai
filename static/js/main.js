function addRow(){
    let items = document.getElementById("items");
    let firstRow = document.querySelector(".bill-row");

    if(firstRow){
        let newRow = firstRow.cloneNode(true);
        newRow.querySelector("input").value = 1;
        items.appendChild(newRow);
    }
}

window.onload = function(){

    let barCanvas = document.getElementById("salesBarChart");

    if(barCanvas){
        let labels = JSON.parse(barCanvas.dataset.labels);
        let values = JSON.parse(barCanvas.dataset.values);

        new Chart(barCanvas, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Units Sold",
                    data: values,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true
            }
        });
    }

    let donutCanvas = document.getElementById("salesDonutChart");

    if(donutCanvas){
        let labels = JSON.parse(donutCanvas.dataset.labels);
        let values = JSON.parse(donutCanvas.dataset.values);

        new Chart(donutCanvas, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    label: "Sales Share",
                    data: values
                }]
            },
            options: {
                responsive: true
            }
        });
    }

};
