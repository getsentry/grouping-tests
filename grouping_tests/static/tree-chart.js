// Tree chart
// Inspired by https://livebook.manning.com/book/d3js-in-action-second-edition/chapter-6/v-6/38

function renderTreeChart(data, weighItemCount) {

    var root = d3.hierarchy(data);
    root = weighItemCount ? root.sum(d => d.item_count) : root.count();

    const svg = document.getElementById('tree-chart');
    if(svg === null) return;

    svg.innerHTML = ''; // Clear previous renderings

    const width = parseInt(svg.parentElement.clientWidth);

    const layerHeight = 40;
    const height = (root.height + 1) * layerHeight;
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);

    var partitionLayout = d3.partition().size([width, height]).round(true);

    partitionLayout(root);

    const colors = ["#5EAFC6", "#FE9922", "#93c464", "#75739F"];
    var colorIndex = 0;
    function color(node) {
        var rv
        if (node.parent && node.parent.color && node.parent.children.length == 1) {
            rv = node.parent.color
        } else {
            rv = colors[colorIndex++ % colors.length];
        }

        node.color = rv;
        return rv;
    }

    const nodes = d3
        .select(svg)
        .selectAll("g")
        .data(root.descendants())
        .enter()
        .append("g")
        .attr("transform", function (d) {
            return "translate(" + [d.x0, d.y0] + ")";
        });

    const anchors = nodes.append("a").attr("href", (d) => d.data.href);

    anchors
        .append("rect")
        .attr("width", (d) => {
            const w = d.x1 - d.x0;
            return w;
        })
        .attr("height", (d) => d.y1 - d.y0)
        .style("fill", color)
        .style("stroke", "white");

    anchors
        .append("text")
        .attr("dx", 8)
        .attr("dy", 25)
        .text((d) => (d.x1 - d.x0) && d.data.name)
        .style("fill", "white");
}
