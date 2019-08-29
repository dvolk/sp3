$(document).ready(function changeOutputDir() {
    var outProj = document.getElementById("project-output").value;
    document.getElementById("header-workdir").innerHTML = "Output Directory: "  + outProj;
});