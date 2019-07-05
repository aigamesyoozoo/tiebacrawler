// to update
// data.x
// endpoint

var folderName = "i am the GLOBAL folderName for weibo!";
var components = ["postsContainer"];
var data2 = [];

function getAnalysis(newFolder) {
  folderName = newFolder;
  var endpoint = "/main/api/history/weibo";
  $.ajax({
    method: "GET",
    url: endpoint,
    data: {
      folder: folderName
    },
    success: function(data) {
      if (data == null) {
        visibility(components.slice(0, 1), "none");
      } else {
        data2 = data;
        visibility(components.slice(0, 1), "inline-block");
        displayPosts(data);
      }
    },
    error: function(err) {
      console.log("error");
      console.log(err);
      visibility(components, "none");
    }
  });
}

// repeated
function visibility(selected, displayOption) {
  selected.forEach(function(item) {
    document.getElementById(item).style.display = displayOption;
  });
}

function displayPosts(data) {
  let table = document.querySelector("table");
  let headers = Object.keys(data2[0]);
  generateTable(table, data2);
  generateTableHead(table, headers);
  $("#poststable").DataTable();
}

function generateTableHead(table, data) {
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
      let cell = row.insertCell();
      let text = document.createTextNode(element[key]);
      cell.appendChild(text);
    }
  }
}

// $(document).ready(function() {
//   $("#poststable").DataTable();
//   // $(".dataTables_length").addClass("bs-select");
// });
