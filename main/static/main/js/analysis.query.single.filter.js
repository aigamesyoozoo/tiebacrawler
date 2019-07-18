var endpoint = "";
var history_dict = {};
var filter1 = "media";

function setQuerybar(url) {
  endpoint = url;
  $.ajax({
    method: "GET",
    url: url,
    success: function(data) {
      if (data.users) create_options(filter1, data.users);
    },
    error: function(err) {
      console.log("error");
      console.log(err);
    }
  });
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

  getAnalysis(document.getElementById(filter1).value);
}
