/* ABCdb static/stats_bar_chart.js - bar charts for stats view
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

/* Horizonal bar chart: logarithmic X-axis, ordinal Y-axis (a set of integers)
 * Requires: D3 v4, a reasonably modern browser.
 */

/* The margins between inner portion of chart and outside of SVG element;
 * these need to include space for the axes and labels.
 */
var margin = {top: 40, right: 20, bottom: 70, left: 60};

/* Total chart height depends on number of bars, but is never less than that needed for
 * `minBars` bars (to leave space for Y-axis labels). */
var barHeight = 20,
    minBars = 6;

function translate(x, y) {
    /* Return a translate string for an SVG transform attribute. */
    return "translate(" + x + "," + y + ")";
}

function create_chart(id, data, yLabel) {
    /* inner size of chart, not counting axes and labels */
    var innerWidth = 560,
        innerHeight = barHeight * data.length,
        innerYOffset = data.length < minBars ? (0.5 * barHeight * (minBars - data.length)) : 0;

    var svgWidth = innerWidth + margin.left + margin.right,
        svgHeight = innerHeight + 2 * innerYOffset + margin.top + margin.bottom;

    var x = d3.scaleLog()
        /* Beginning the domain at 0.5 means '1' and '2' don't look odd side-by-side. */
        .domain([0.5, d3.max(data, function(d) { return d.frequency; })])
        .range([0, innerWidth]);

    var y = d3.scaleBand()
        .domain(data.map(function(d) { return d.count; }))
        .range([0, innerHeight])
        .padding(0.1);

    var xAxis = d3.axisBottom()
        .scale(x)
        .ticks(4, ",.1s") /* This gives nice ticks and labels at powers of ten. */
        .tickSize(6, 0);

    var yAxis = d3.axisLeft()
        .scale(y)
        .tickSize(0) /* no ticks */
        .tickPadding(8); /* but keep the bar labels outside the bars */

    /* add SVG element */
    var chart = d3.select("#" + id)
      .append("svg")
        .attr("width", svgWidth)
        .attr("height", svgHeight)
        .attr("class", "chart");

    /* inner group for the chart itself */
    var inner = chart.append("g")
        .attr("transform", translate(margin.left, margin.top + innerYOffset));

    /* bars */
    var bar = inner.selectAll("g")
        .data(data)
      .enter().append("g")
        .attr("transform", function(d, i) { return translate(0, i * barHeight); });

    bar.append("rect")
        .attr("x", 0).attr("y", 0)
        .attr("width", function(d) { return x(d.frequency); })
        .attr("height", barHeight - 1);

    bar.append("text")
        .attr("x", function(d) { return x(d.frequency) - 3; })
        .attr("y", barHeight / 2)
        .attr("dy", ".35em")
        .text(function(d) { return d.frequency; });

    /* X axis and label */
    chart.append("g")
        .attr("class", "x axis")
        .attr("transform", translate(margin.left, svgHeight - innerYOffset - margin.bottom + 2))
        .call(xAxis)
      .append("text")
        .attr("y", 32)
        .attr("x", innerWidth / 2)
        .text("Frequency of Occurrence (logarithmic)");

    /* Y axis and label */
    var txt = chart.append("g")
        .attr("class", "y axis")
        .attr("transform", translate(margin.left - 4, innerYOffset + margin.top))
        .call(yAxis)
      .append("text")
        .attr("transform", "rotate(-90)");

    if (data.length <= 7) {  /* split Y-axis label if fewer than 8 bars */
        var lines = yLabel.split("\n");
        txt.append("tspan")
            .attr("y", -36)
            .attr("x", -innerHeight / 2)
            .text(lines[0]);
        txt.append("tspan")
            .attr("dy", "1.2em")
            .attr("x", -innerHeight / 2)
            .text(lines[1]);
    } else {
        txt.attr("y", -24)
            .attr("x", -innerHeight / 2)
            .text(yLabel.replace("\n", " "));
    }
}

create_chart("inst_per_song", inst_per_song, "Instances-per-Song\nCount");
create_chart("coll_per_inst", coll_per_inst, "Collections-per-Instance\nCount");
