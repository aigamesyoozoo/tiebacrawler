var folderName = "i am the GLOBAL folderName!";

var components = [
  "popContainer",
  "summContainer",
  "sentiContainer",
  "kwContainer",
  "searchContainer"
];

function getAnalysis(newFolder) {
  folderName = newFolder;
  var endpoint = "/main/api/chart/analysis";
  $.ajax({
    method: "GET",
    url: endpoint,
    data: {
      folder: folderName
    },
    success: function(data) {
      if (data.forums == null) {
        visibility(components.slice(0, 1), "none");
      } else {
        visibility(components.slice(0, 1), "inline-block");
        displayPopularTieba(data.forums);
      }
      if (data.summary == null) {
        visibility(components.slice(1, 5), "none");
      } else {
        visibility(components.slice(1, 5), "inline-block");
        displaySummary(data.summary, data.stats.replies_count);
        displaySentiments(data.sentiments);
        displayKeywords(data.keywords);
      }
      visibility(components.slice(4, 5), "none");
    },
    error: function(err) {
      console.log("error");
      console.log(err);
      visibility(components, "none");
    }
  });
}

function getKeywordSearch(search_input) {
  var endpoint = "/main/api/chart/keywordsearch/";

  $.ajax({
    method: "GET",
    url: endpoint,
    data: {
      folder: folderName,
      search_input: search_input
    },
    success: function(data) {
      if (data == null) {
        visibility(components.slice(4, 5), "none");
      } else {
        visibility(components.slice(4, 5), "inline-block");
        displayKeywordSearch(data);
      }
    },
    error: function(err) {
      console.log("error");
      console.log(err);
      visibility(components.slice(4, 5), "none");
    }
  });
}

function visibility(selected, displayOption) {
  selected.forEach(function(item) {
    document.getElementById(item).style.display = displayOption;
  });
}

function displayPopularTieba(data) {
  var ul = document.getElementById("popular");
  ul.innerHTML = "";
  Object.keys(data).forEach(function(item, index, array) {
    var li = document.createElement("li");
    ul.appendChild(li);
    li.innerHTML =
      item + ' <span class="badge badge-warning">' + data[item] + "hits</span>";
  });
}

function displaySummary(data, replies_count) {
  var ul = document.getElementById("summary");
  ul.innerHTML = "";

  data.forEach(function(item, index, array) {
    var li = document.createElement("li");
    ul.appendChild(li);
    li.innerHTML =
      '<a href="' + item[1] + '"  target="_blank">"' + item[0] + '"</a>';
  });

  var span = document.getElementById("replies_count");
  span.innerHTML = replies_count;
}

function displayKeywords(data) {
  resetCanvasAndContainers(
    "kwContainerContainer",
    "kwContainer",
    "keywordChart"
  );

  displayBarChart(
    "horizontalBar",
    "keywordChart",
    "Frequency",
    Object.keys(data),
    Object.values(data)
  );
}

function displayKeywordSearch(data) {
  resetCanvasAndContainers(
    "searchContainerContainer",
    "searchContainer",
    "searchChart"
  );

  displayBarChart(
    "horizontalBar",
    "searchChart",
    "Frequency",
    Object.keys(data),
    Object.values(data)
  );
}

function displaySentiments(data) {
  resetCanvasAndContainers(
    "sentiContainerContainer",
    "sentiContainer",
    "sentimentChart"
  );

  rawValues = Object.values(data);
  rawValues.forEach(function(item, index) {
    rawValues[index] = parseInt(item);
  });
  rawKeys = Object.keys(data);
  keysWithPercentage = new Array(3).fill(0);

  const sum = rawValues.reduce((a, b) => a + b, 0);
  if (sum > 0) {
    rawValues.forEach(function(item, index) {
      var percent = ((item / sum) * 100).toFixed(1);
      keysWithPercentage[index] = rawKeys[index] + " (" + percent + "%)";
    });
  }

  displayPieChart(
    "doughnut",
    "sentimentChart",
    "Sentiment Analysis",
    keysWithPercentage,
    rawValues
  );
}

function resetCanvasAndContainers(parent, child, chart) {
  //Need to remove parent of parent container, else multiple iframes would be appended to it after multiple selections
  html =
    '<div id="' +
    child +
    '"><canvas id="' +
    chart +
    '" width="400" height="400"></canvas></div>';
  parent = "#" + parent;
  child = "#" + child;
  $(child).remove();
  $(parent).append(html);
}

function displayBarChart(chartType, id, title, labels, data) {
  var canvas = document.getElementById(id);

  var myChart = new Chart(canvas, {
    type: chartType,
    data: {
      labels: labels,
      datasets: [
        {
          label: title,
          data: data,
          backgroundColor: [
            "rgba(255, 99, 132, 0.2)",
            "rgba(54, 162, 235, 0.2)",
            "rgba(255, 206, 86, 0.2)",
            "rgba(75, 192, 192, 0.2)",
            "rgba(153, 102, 255, 0.2)",
            "rgba(255, 159, 64, 0.2)"
          ],
          borderColor: [
            "rgba(255, 99, 132, 1)",
            "rgba(54, 162, 235, 1)",
            "rgba(255, 206, 86, 1)",
            "rgba(75, 192, 192, 1)",
            "rgba(153, 102, 255, 1)",
            "rgba(255, 159, 64, 1)"
          ],
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        yAxes: [
          {
            ticks: {
              beginAtZero: true,
              fontSize: 16,
              precision: 0
            }
          }
        ],
        xAxes: [
          {
            ticks: {
              beginAtZero: true,
              fontSize: 16,
              callback: function(value, index, values) {
                if (Math.floor(value) === value) {
                  return value;
                }
              }
            }
          }
        ]
      },
      legend: {
        display: false
      }
    }
  });
}

function displayPieChart(chartType, id, title, labels, data) {
  var canvas = document.getElementById(id);
  var myChart = new Chart(canvas, {
    type: chartType,
    data: {
      labels: labels,
      datasets: [
        {
          label: title,
          data: data,
          backgroundColor: [
            "rgba(75, 192, 192, 0.2)",
            "rgba(255, 99, 132, 0.2)",
            "rgba(255, 206, 86, 0.2)"
          ],
          borderColor: [
            "rgba(75, 192, 192, 1)",
            "rgba(255, 99, 132, 1)",
            "rgba(255, 206, 86, 1)"
          ],
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        labels: {
          render: "percentage",
          fontColor: ["green", "white", "red"],
          precision: 2
        }
      }
    }
  });
}
