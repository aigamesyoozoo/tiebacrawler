var now = new Date();
var year_select = ['start_date_year', 'end_date_year'];
var month_select = ['start_date_month', 'end_date_month'];
year_select.forEach(createYearsOptions);
month_select.forEach(createMonthsOptions);

function createYearsOptions(item, index) {
    var max = now.getFullYear();
    var min = max-7;
    select = document.getElementById(item);

    for (var i = max; i>=min; i--){
    var opt = document.createElement('option');
    opt.value = i;
    opt.innerHTML = i;
    select.appendChild(opt);
    }
}

function createMonthsOptions(item, index) {
    curr_month = now.getMonth()+1;
    select = document.getElementById(item);

    for (var i = 1; i<=12; i++){
    var opt = document.createElement('option');
    opt.value = i.toString();
    opt.innerHTML = i;
    if (i == curr_month) {
        opt.setAttribute("selected","selected");
    }
    select.appendChild(opt);
    }
}