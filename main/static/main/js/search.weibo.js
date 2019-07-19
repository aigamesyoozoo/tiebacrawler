function validate() {
  var keyword = document.forms["weibo_form"]["keyword"].value;
  var Is_overrided = true;

  $.ajax({
    type: "POST",
    async: false,
    url: "/main/validate/",
    data: {
      keyword: keyword,
      task_type: "weibo"
    },
    dataType: "json",
    success: function(data) {
      if (!data.ongoing_task) {

        if (data.info_dict) {
          setSubmitCancelDetails(data.info_dict);

          if (data.Is_existed) {
            if (
              !confirm(
                "The selected user has been already crawled before, would you want to continue and override the previous data?"
              )
            ) {
              Is_overrided = false;
            } else {
              Is_overrided = true;
            }
          } else {
            Is_overrided = true;
          }
        }
      } else {
          alert(
            'This Weibo is currently being crawled and its data will be available in the "History-Weibo" tab soon. You may wish to crawl a different Weibo user.'
          );
          Is_overrided = false;
      }
    }
  });

  if (Is_overrided) {
    downloadView();
  } else {
    return false;
  }
}

function setSubmitCancelDetails(info) {
  console.log("inside setSubmitCancelDetails()");
  document.forms["weibo_form"]["uid"].value = info.uid;
  document.forms["weibo_form"]["uname"].value = info.uname;
  document.forms["cancel"]["task_type"].value = "weibo";
  document.forms["cancel"]["id"].value = info.uname;
}

function downloadView() {
  // Values
  document.getElementById("keyword").textContent =
    document.forms["weibo_form"]["keyword"].value;

  // Visibility
  var download_segment = document.getElementById("download_segment");
  var query_segment = document.getElementById("query_box");
  download_segment.style.display = "block";
  query_segment.style.display = "none";
}
