(function (Phylocanvas) {
    var tree = Phylocanvas.createTree('phylocanvas');
    tree.setTreeType('rectangular')
    tree.setNodeSize(1);
    tree.setTextSize(20);
    tree.lineWidth = 1;
    tree.on('error', function (event) { throw event.error; });
    tree.on('loaded', function () {
        console.log('loaded');
    });
    var tree_input = document.getElementById("nwk_tree").innerHTML;
    tree.load(tree_input);
    window.tree = tree // closure out
})(window.Phylocanvas);

for (var i = 0; i < tree.leaves.length; i++) {
    var label = tree.leaves[i].label;
    label = label.replace("_", " (");
    label = label.concat(")");
    tree.leaves[i].label = label;
    var guid = document.getElementById("guid").innerHTML;
    if (label.includes(guid)) {
        tree.leaves[i].highlighted = true;
    }
}

$('.btn').click(function (e) {
    document.getElementById("phylocanvas").hidden = false;

    var tree_input = document.getElementById("nwk_tree").innerHTML;
    var radioValue = $(e.target.children[0]).val()
    if (radioValue) {
        tree.setTreeType(radioValue);
    }
    tree.load(tree_input);
});

