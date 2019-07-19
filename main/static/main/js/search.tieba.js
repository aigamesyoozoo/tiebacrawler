function submit_task(
  keyword,
  start_date_year,
  start_date_month,
  end_date_year,
  end_date_month
) {
  $.ajax({
    type: "POST",
    async: false,
    url: "/main/crawl/tieba/",
    data: {
      keyword: keyword,
      start_date_year: start_date_year,
      start_date_month: start_date_month,
      end_date_year: end_date_year,
      end_date_month: end_date_month
    },
    dataType: "json",
    success: function(data) {
      setSubmitCancelDetails(data);
    }
  });
}

function setSubmitCancelDetails(data) {
  document.forms["query_form"]["task_id"].value = data.task_id;
  document.forms["cancel"]["task_type"].value = "tieba";
  document.forms["cancel"]["id"].value = data.task_id;
}

function validate() {
  var start_date_year = document.forms["query_form"]["start_date_year"].value;
  var start_date_month = document.forms["query_form"]["start_date_month"].value;
  var end_date_year = document.forms["query_form"]["end_date_year"].value;
  var end_date_month = document.forms["query_form"]["end_date_month"].value;
  var start_date = new Date(start_date_year, start_date_month);
  var end_date = new Date(end_date_year, end_date_month);
  var keyword = document.forms["query_form"]["keyword"].value;
  var Is_overrided;

  if (start_date > end_date) {
    alert("Start date should be same or earlier than end date.");
    return false;
  } else {
    Is_overrided = true;
  }

  $.ajax({
    type: "POST",
    async: false,
    url: "/main/validate/",
    data: {
      keyword: keyword,
      start_date_year: start_date_year,
      start_date_month: start_date_month,
      end_date_year: end_date_year,
      end_date_month: end_date_month,
      task_type: "tieba"
    },
    dataType: "json",
    success: function(data) {
      if (!data.is_ongoing_task) {
        if (data.Is_existed) {
          if (
            !confirm(
              "The selected tieba with this date range has been already crawled before, would you want to continue and override the previous data?"
            )
          ) {
            Is_overrided = false;
          } else {
            Is_overrided = true;
          }
        } else {
          Is_overrided = true;
        }
      } else {
        alert(
          'This Tieba and date range is currently being crawled and its data will be available in the "History-Tieba" tab soon. Please select a different Tieba/date range for crawling.'
        );
        Is_overrided = false;
      }
    }
  });

  if (Is_overrided) {
    submit_task(
      keyword,
      start_date_year,
      start_date_month,
      end_date_year,
      end_date_month
    );
    downloadView();
  } else {
    return false;
  }
}

function downloadView() {
  // Values
  document.getElementById("keyword").textContent =
    document.forms["query_form"]["keyword"].value;

  // Visibility
  var download_segment = document.getElementById("download_segment");
  var query_segment = document.getElementById("query_segment");
  download_segment.style.display = "block";
  query_segment.style.display = "none";
}