var endpoint = "";
var history_dict = {};
var filter1 = "media";
var filter2 = "dates";


function setQuerybar(url){
  endpoint = url;
  $.ajax({
    method: "GET",
    url: url,
    success: function(data) {
      history_dict = data;
      initializePage();
    },
    error: function(err) {
      console.log("error");
      console.log(err);
    }
  });
}


function initializePage() {
  var hist = Object.keys(history_dict);
  create_options(filter1, hist);
  display_past_crawls(hist[0]);
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


function display_past_crawls(tieba) {
  create_options("dates", history_dict[tieba]);
  getFolder();
}


function getFolder() {
  newFolder =
    document.getElementById(filter1).value +
    "_" +
    document.getElementById(filter2).value;
  getAnalysis(newFolder);
}