$(document).ready(function () {
    $(".tablesorter").tablesorter();
    $(".tablesorter").tablesorter({ sortList: [[0, 0], [1, 0]] });
});

$(document).on('click', '#delete_link', function(e){
    if(!confirm($(this).data('confirm'))){
      e.stopImmediatePropagation();
      e.preventDefault();
    }
});

$(document).on('click', '#delete_output', function(e){
    if(!confirm($(this).data('confirm'))){
      e.stopImmediatePropagation();
      e.preventDefault();
    }
});

$(document).on('click', '#delete_run', function(e){
    if(!confirm($(this).data('confirm'))){
      e.stopImmediatePropagation();
      e.preventDefault();
    }
});

$(document).on('click', '#submit_pipeline', function(e){
     var selected_option = $("#flow_option option:selected").html();
     var selected_flow = $("#selected_flow").html();
     if (selected_option !== selected_flow) {
     	if(!confirm($(this).data('confirm'))){
    	   e.stopImmediatePropagation();
	   e.preventDefault();
	}
      }
});
