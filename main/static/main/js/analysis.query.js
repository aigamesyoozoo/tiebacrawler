// display tiebas upon page load
var endpoint = "/main/api/history/tieba";
var history_dict = {};

$.ajax({
  method: "GET",
  url: endpoint,
  success: function(data) {
    history_dict = data;
    initializePage();
  },
  error: function(err) {
    console.log("error");
    console.log(err);
  }
});

function getFolder() {
  newFolder =
    document.getElementById("tieba").value +
    "_" +
    document.getElementById("dates").value;
  getAnalysis(newFolder);
}

function initializePage() {
  var hist = Object.keys(history_dict);
  create_options("tieba", hist);
  display_past_crawls(hist[0]);
}

function display_past_crawls(tieba) {
  create_options("dates", history_dict[tieba]);
  getFolder();
}

function create_options(id, arr) {
  select = document.getElementById(id);
  select.innerHTML = ""; // remove options of previous id

  arr.forEach(function(element) {
    var opt = document.createElement("option");
    opt.value = element;
    opt.innerHTML = element;
    select.appendChild(opt);
  });
}
