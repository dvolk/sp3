var tree_input_element = document.getElementById("nwk_tree");
var tree_input = tree_input_element.innerHTML;

if (tree_input.length > 0) {
    var target_node = "NOTARGET";
    var target_node_element = document.getElementById("name");
    if (target_node_element !== null) {
        target_node = target_node_element.innerHTML;
    }

    var tree = d3.layout.phylotree()
        .options({
            brush: false,
            zoom: true,
            "show-scale": false,
            "transitions": false
        })
        .svg(d3.select("#tree_display"));
    tree(tree_input).layout();

    tree.modify_selection(function (d) {
        if (target_node !== undefined && d.target.name.startsWith(target_node)) {
            console.log(d.target.name);
            return true;
        }
    })

    tree.update()

    var which_function = tree.spacing_x;
    which_function(which_function() + (+ 5)).update();

    var which_function = tree.spacing_y;
    which_function(which_function() + (+ 5)).update();
}


$("#layout").on("click", function (e) {
    tree.radial($(this).prop("checked")).placenodes().update();
});

$(".phylotree-layout-mode").on("change", function (e) {
    if ($(this).is(':checked')) {
        if (tree.radial() != ($(this).data("mode") == "radial")) {
            tree.radial(!tree.radial()).placenodes().update();
        }
    }
});

$("[data-direction]").on("click", function (e) {
    var which_function = $(this).data("direction") == 'vertical' ? tree.spacing_x : tree.spacing_y;
    which_function(which_function() + (+ $(this).data("amount"))).update();
});
