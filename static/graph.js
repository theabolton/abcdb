/* ABCdb static/graph.js - Tune Graph Visualization
 *
 * Copyright © 2017 Sean Bolton.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 * LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 * WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

/* Requires: D3 v4, dagre-d3v4, a reasonably modern browser. */

var focus_node, g, graph_serial, svg, svg_g;

/* initialize_graph()
 *
 * Run at first load, makes initial graph request.
 */
function initialize_graph() {
    /* retrieve focus node from URL */
    var focus_re = new RegExp("/graph/([tsi]\\d+)");
    var result = focus_re.exec(window.location.href);
    if (result === null) {
        display_error("Unable to parse URL.");
        return;
    }

    /* initialize global variables */
    focus_node = result[1];

    g = new dagreD3.graphlib.Graph()
           .setGraph({})
           .setDefaultEdgeLabel(function() { return {}; });

    graph_serial = 0; /* incremented for each new graph */

    svg = d3.select("#graph").append("svg")
              .attr("width", 960).attr("height", 480)
              .attr("xmlns", d3.namespaces.svg)
              .attr("xmlns:xlink", d3.namespaces.xlink);
    svg_g = svg.append("g");

    /* request the graph data */
    request_graph(focus_node);
}

/* request_graph()
 *
 * Make an Ajax request for the given node id.
 */
function request_graph(id) {
    d3.json("/ajax/graph/" + id + "/")
        .header("X-Requested-With", "XMLHttpRequest")
        .get(load_graph);
}

/* display_error()
 *
 * Replace contents of <div id="graph> with a text error message.
 */
function display_error(message) {
    d3.select("#graph").html("<p>Oops. " + message + " Try starting over with a new " +
                             "<a href=\"/search/\">search</a>.</p>");
}

/* load_graph()
 *
 * Callback for the Ajax request. Handle any errors, or (re)build and display the graph.
 */
function load_graph(error, json) {
    /* handle XHR error, if any */
    if (error) {
        if (error.target.status === 0) {
            display_error("An error occurred while trying to request the tune graph ('" +
                          error.target.status + " " + error.target.statusText + "').");
        } else {
            display_error("Tune graph loading failed with '" + error.target.status +
                          " " + error.target.statusText + "'.");
        }
        return;
    }
    /* handle back-end error, if any */
    if (json.error) {
        display_error("The server replied with '" + json.description + "'.");
        return;
    }

    var transition_time = 500;
    var node, link, attributes, i;

    /* graph_serial is used to mark each node and link as it is created or updated. Nodes
     * and links with a stale graph_serial are no longer present in the graph and can be
     * removed. */
    graph_serial += 1;

    /* build nodes */
    json.nodes.sort(function(a, b) { return Number(a.id.slice(1)) - Number(b.id.slice(1)); });
    for (i = 0; i < json.nodes.length; i++) {
        node = json.nodes[i];
        attributes = { shape: "ellipse", serial: graph_serial };
        if (g.node(node.id) == undefined) {
            //console.log("Adding node " + node.id);
        } else {
            transition_time = 1000;
        }
        switch(node.id.charAt(0)) {
          case "s":
            attributes.class = "song";
            attributes.label = "Song " + node.id.slice(1);
            break;
          case "t":
            attributes.class = "title";
            attributes.label = "Title " + node.id.slice(1);
            break;
          case "i":
            attributes.class = "instance";
            attributes.label = "Instance " + node.id.slice(1);
            break;
        }
        if (node.title) {
            attributes.label += "\n“" + node.title + "”";
        }
        //if (node.id != focus_node && node.id.charAt(0) == focus_node.charAt(0)) {
        if (node.id != focus_node) {
            attributes.class += " blur";
        }
        g.setNode(node.id, attributes);
    }
    /* build edges */
    for (i = 0; i < json.links.length; i++) {
        link = json.links[i];
        attributes = { curve: d3.curveMonotoneX, serial: graph_serial };
        if (link.source != focus_node && link.target != focus_node) {
            attributes.class = "blur";
        } else {
            attributes.weight = 4; /* pull linked nodes closer to focus node */
        }
        g.setEdge(link.source, link.target, attributes);
    }
    /* set attributes of current nodes, or remove stale nodes */
    g.nodes().forEach(function(v) {
        node = g.node(v);
        /* make the ellipses a little bigger */
        if (node.serial == graph_serial) {
            node.paddingX = 20;
            node.paddingTop = 12;
            node.paddingBottom = 16;
        } else {
            //console.log("Removing node " + v);
            g.removeNode(v);  /* will also remove adjacent edges */
        }
    });

    //g.nodes().forEach(function(v) {
    //    console.log(g.node(v)); // "Node " + v + ": " + JSON.stringify(g.node(v)));
    //});
    //g.edges().forEach(function(e) {
    //    console.log(g.edge(e)); // "Edge " + e.v + " -> " + e.w + ": " + JSON.stringify(g.edge(e)));
    //});

    /* set graph-level properties */
    g.graph().rankdir = "LR";
    // g.graph().align = "DR";  /* default seems to be 'DL' */
    // g.graph().ranker = "tight-tree"; /* or "network-simplex" (default) or "longest-path"; */
    g.graph().ranksep = 90;
    // g.graph().edgesep = 20;
    g.graph().nodesep = 16;
    g.graph().transition = function(selection) {
      return selection.transition().duration(transition_time);
    };

    /* render the graph */
    var render = new dagreD3.render();
    render(svg_g, g);

    /* dagre-d3(v4) doesn't update the classes on already-existent edgePaths (like it does
     * for nodes), so we have to do that here */
    svg.selectAll("g.edgePath").each(function(_d, _i, _nodes) {
        if (_d.v == focus_node || _d.w == focus_node) {
            this.classList.remove("blur");
        } else {
            this.classList.add("blur");
        }
    });

    /* make nodes clickable */
    svg.selectAll("g.node").each(function(_d, _i, _nodes) {
            /* wrap the contents of each node group in an <a xlink:href=...> tag... */
            var href;
            if (_d == focus_node) {
                switch (focus_node.charAt(0)) {
                  case "s":  href = "/song/"     + focus_node.slice(1) + "/"; break;
                  case "t":  href = "/title/"    + focus_node.slice(1) + "/"; break;
                  case "i":  href = "/instance/" + focus_node.slice(1) + "/"; break;
                }
            } else {
                href = "/graph/" + _d + "/";
            }
            var a = document.createElementNS(d3.namespaces.svg, "a");
            a.setAttributeNS(d3.namespaces.xlink, "href", href);
            this.appendChild(a);
            while (this.childNodes.length > 1) {
                a.appendChild(this.firstChild);
            }
            /* ...but wire the click event to our Ajax handler */
            d3.select(this).select("a")
                .on("click", on_click);
    });

    /* center graph */
    svg_g.transition().duration(transition_time)
        .attr("transform", "translate(" + ((svg.attr("width") - g.graph().width) / 2) + ", 20)");
    svg.transition().duration(transition_time).attr("height", g.graph().height + 40);
}

/* click event handler for nodes */
function on_click(_d, _i, _nodes) {
    /* may not be able to rely on _i and _nodes across graph loads! */
    if (_d != focus_node) {
        d3.event.preventDefault();
        // this - DOM element
        // _d - node id (e.g. "s803")
        // g.node(_d) - graph node
        focus_node = _d;
        request_graph(_d);
    } else {
        /* If this is the focus node, we let its default action take us to the node's
         * detail page. */
    }
}

initialize_graph();
