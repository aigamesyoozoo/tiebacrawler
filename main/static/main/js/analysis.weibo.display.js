var components = ["postsContainer"];

function getAnalysis(folderName) {
  var endpoint = "/main/api/table/posts/";
  $.ajax({
    method: "GET",
    url: endpoint,
    data: {
      folder: folderName
    },
    success: function(data) {
      if (data) {
        visibility(components.slice(0, 1), "inline-block");
        displayPosts(data);
      } else {
        visibility(components.slice(0, 1), "none");
      }
    },
    error: function(err) {
      console.log("error");
      console.log(err);
      visibility(components, "none");
    }
  });
}

function visibility(selected, displayOption) {
  selected.forEach(function(item) {
    document.getElementById(item).style.display = displayOption;
  });
}

function displayPosts(data) {
  let table = document.querySelector("table");
  $("#poststable > thead").html("");
  $("#poststable > tbody").html("");
  console.log(data);
  generateTable(table, data); // Need to generate data before head, else data will be populated in thead instead of tbody
  generateTableHead(table);
  if (!$.fn.dataTable.isDataTable("#poststable")) {
    $("#poststable").DataTable({
      columnDefs: [{ width: 400, targets: 0 }]
    });
  }
  let postsContainer = document.getElementById("postsContainer");
  postsContainer.style.display = "block";
  console.log(postsContainer.style.display);
}

function generateTableHead(table) {
  data = [
    "Post Description",
    "Date Created",
    "Link",
    "# Reposts",
    "# Comments",
    "# Attitudes"
  ];
  let thead = table.createTHead();
  let row = thead.insertRow();
  for (let key of data) {
    let th = document.createElement("th");
    let text = document.createTextNode(key);
    th.appendChild(text);
    row.appendChild(th);
  }
}

function generateTable(table, data) {
  for (let element of data) {
    let row = table.insertRow();
    for (key in element) {
      let node;
      let cell = row.insertCell();
      if (key == "scheme") {
        node = document.createElement("a");
        node.setAttribute("href", element[key]);
        node.setAttribute("target", "_blank");
        node.innerHTML = "View";
      } else {
        node = document.createTextNode(element[key]);
      }
      cell.appendChild(node);
    }
  }
}
