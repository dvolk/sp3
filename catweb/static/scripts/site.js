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

$(document).on('change', '#check_all_neighbour', function(e){
    if (document.getElementById('check_all_neighbour').checked) {
	$('.neighbour_tick').each(function () {
	    $(this).trigger('click');
	    $(this).prop("checked", true);
	});
    }
    else {
	$('.neighbour_tick').each(function () {
	    $(this).trigger('click');
	    $(this).prop("checked", false);
	});
    }
});

$(document).on('change', '#tick_my_org', function(e){
    var query_org = document.getElementById('query_run').innerHTML.split('-')[0]
    console.log(query_org)

    if (document.getElementById('tick_my_org').checked) {
	$('.neighbour_tick').each(function () {
	    var org = $(this)[0].defaultValue.split('-')[0]
	    if (org === query_org) {
                $(this).trigger('click');
	        $(this).prop("checked", true);
	    }
	    console.log(org)
	});
    }
    else {
	$('.neighbour_tick').each(function () {
	    var org = $(this)[0].defaultValue.split('-')[0]
	    if (org === query_org) {
                $(this).trigger('click');
	        $(this).prop("checked", false);
	    }
	    console.log(org)
	});
    }
});

$(document).on('change', '#tick_other_orgs', function(e){
    var query_org = document.getElementById('query_run').innerHTML.split('-')[0]
    console.log(query_org)

    if (document.getElementById('tick_other_orgs').checked) {
	$('.neighbour_tick').each(function () {
	    var org = $(this)[0].defaultValue.split('-')[0]
	    if (org !== query_org) {
                $(this).trigger('click');
	        $(this).prop("checked", true);
	    }
	    console.log(org)
	});
    }
    else {
	$('.neighbour_tick').each(function () {
	    var org = $(this)[0].defaultValue.split('-')[0]
	    if (org !== query_org) {
                $(this).trigger('click');
	        $(this).prop("checked", false);
	    }
	    console.log(org)
	});
    }
});

$(document).on('click', '#build_tree', function(e){
    var samples = $('.neighbour_tick')
    var ticked = 0
    for (var i=0; i<samples.length; i++){
	if (samples[i].checked == true){
	    ticked = ticked + 1;
	}
    }

    if (ticked < 3) {
        alert("Please select three and more samples. ")
	e.preventDefault();
    	e.stopPropagation();

      }

});

$(document).on('click', '#search_btn', function(e){
    window.Phylocanvas.draw();
    search_text = document.getElementById('search_node').value;
    leaves = window.Phylocanvas.leaves;
     for (i=0; i< leaves.length; i++) {
         if (leaves[i].label.includes(search_text)) {
            leaves[i].highlighted = true;
        }
    }
    window.Phylocanvas.draw();
});

$(document).on('click', '#reset_btn', function(e){
    tree = window.Phylocanvas;
    tree.setNodeSize(20);                                                                                                                             tree.lineWidth = 2;
    tree.redrawOriginalTree();
    tree.setTextSize(30);
});
