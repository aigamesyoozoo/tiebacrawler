function submit_task(
    keyword,
  ) {
    $.ajax({
      type: "POST",
      async: false,
      url: "/main/weibo/",
      data: {
        keyword: keyword,
      },
      dataType: "json",
      success: function(data) {}
    });
  }
  
  function validate() {
    var keyword = document.forms["weibo_form"]["keyword"].value;
    var Is_overrided  = true;
  
    $.ajax({
      type: "POST",
      async: false,
      url: "/main/validate/",
      data: {
        keyword: keyword,
        task_type: "weibo",
      },
      dataType: "json",
      success: function(data) {
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
    });
  
    if (Is_overrided) {
      
      submit_task(
        keyword,
        );
      downloadView();
    } else {
      return false;
    }
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
  
  $(window).on("unload", function() {
    $.ajax({
      type: "GET",
      url: "/main/cancel/"
    });
  });
  