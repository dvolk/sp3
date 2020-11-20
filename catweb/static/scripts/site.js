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

$(document).on('click', '#check_all_neighbour', function(e){
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
