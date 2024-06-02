//import "./styles.css";
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
//import "cytoscape-context-menus/cytoscape-context-menus.css";
//import "cytoscape-navigator/cytoscape.js-navigator.css";
//import data from "./data2";
var popper = require('cytoscape-popper');
var nodeHtmlLabel = require("cytoscape-node-html-label");
var expandCollapse = require("cytoscape-expand-collapse");
var contextMenus = require("cytoscape-context-menus");
var navigator = require("cytoscape-navigator");

//https://stackoverflow.com/questions/51023231/npm-browserify-import-and-export-may-appear-only-with-sourcetype-module
//https://stackoverflow.com/questions/40029113/syntaxerror-import-and-export-may-appear-only-with-sourcetype-module-g
//npm install --save-dev browser-resolve
//npm install --save-dev esmify
//npm install browserify babelify @babel/preset-env @babel/preset-react @babel/core es2015 --save-dev
//npm install babel-preset-es2015 --save-dev
//browserify app.js -p esmify -o app_browserify.js -d

$.get(
  '/kg/graph/json',
  function (data) {
    //https://codesandbox.io/s/github/gregwu/cytoscape/tree/main/?file=/index.html:331-332
    var style = [
      {
        selector: 'node',
        css: {
          content: 'data(label)',
          'text-wrap': 'wrap',
          //"font-family": "helvetica",
          'font-size': '14px',
          'text-outline-width': '3px',
          'text-outline-color': '#888',
          'text-valign': 'center',
          color: '#fc4e03',
          width: 'data(width)',
          height: 'data(height)',
          // when cytoscape.js 2.5 comes out, could use
          // "width":"label"
          // https://github.com/cytoscape/cytoscape.js/issues/1041
          'border-color': '#000',
          // "shape": "octagon",
          shape: 'data(shape)',
          'text-background-opacity': 1,
          'background-color': '#888'
        }
      },

      //  node classes

      {
        selector: 'node.non_existing',
        style: {
          display: 'none'
        }
      },

      {
        selector: 'node.exactly_one',
        style: {
          'border-width': '4px',
          'border-style': 'solid'
        }
      },

      {
        selector: 'node.at_least_one',
        style: {
          'border-width': '8px',
          'border-style': 'double'
        }
      },

      {
        selector: 'node.at_most_one',
        style: {
          'border-width': '3px',
          'border-style': 'dotted'
        }
      },

      {
        selector: 'node.node_unknown',
        style: {
          'border-width': '0px'
        }
      },

      //  edge classes

      {
        selector: 'edge',
        style: {
          //"content": "data(label)",
          'target-arrow-shape': 'triangle',
          //"target-arrow-fill": "hollow",
          //"source-arrow-fill": "hollow",
          'target-arrow-fill': 'filled',
          'source-arrow-fill': 'filled'
        }
      },

      {
        selector: 'edge.none_to_none',
        style: {
          width: '4px',
          'line-style': 'dashed',
          'target-arrow-shape': 'triangle',
          //"source-arrow-shape": "tee",
          //"mid-source-arrow-shape": "tee",
          //"mid-target-arrow-shape": "triangle",
          'target-arrow-fill': 'filled',
          'source-arrow-fill': 'filled'
        }
      },

      {
        selector: 'edge.all_to_all',
        style: {
          width: '4px',
          'line-style': 'solid'
        }
      },

      {
        selector: 'edge.edge_unknown',
        style: {
          width: '4px',
          'line-style': 'dotted'
        }
      },

      {
        selector: 'edge.total',
        style: {
          'source-arrow-shape': 'circle',
          'source-arrow-fill': 'filled'
        }
      },

      {
        selector: 'edge.functional',
        style: {
          'source-arrow-shape': 'square'
        }
      },

      {
        selector: 'edge.injective',
        style: {
          'target-arrow-shape': 'triangle-backcurve'
        }
      },

      {
        selector: 'edge.surjective',
        style: {
          'target-arrow-fill': 'filled'
        }
      },

      // selection

      {
        selector: 'node:selected',
        style: {
          'overlay-opacity': '0.2'
        }
      },

      {
        selector: 'edge:selected',
        style: {
          'overlay-opacity': '0.2'
        }
      }
    ]

    console.log(data)
    console.log(data.elements)

    var h = function (tag, attrs, children) {
      var el = document.createElement(tag)

      Object.keys(attrs).forEach(function (key) {
        var val = attrs[key]

        el.setAttribute(key, val)
      })

      children.forEach(function (child) {
        el.appendChild(child)
      })

      return el
    }

    var t = function (text) {
      var el = document.createTextNode(text)

      return el
    }

    var $ = document.querySelector.bind(document)

    
    cytoscape.use(dagre);

    if (typeof cytoscape("core", "expandCollapse") === "undefined") {
      expandCollapse(cytoscape);
    }
    if (typeof cytoscape("core", "nodeHtmlLabel") === "undefined") {
      nodeHtmlLabel(cytoscape);
    }
    if (typeof cytoscape("core", "contextMenus") === "undefined") {
      contextMenus(cytoscape);
    }
    if (typeof cytoscape("core", "navigator") === "undefined") {
      navigator(cytoscape);
    }
    if (typeof cytoscape("core", "popper") === "undefined") {
      popper(cytoscape); // register extension
    }
    // var cy = cytoscape({
    //   container: document.getElementById('cy'),
    //   minZoom: 1e-20,
    //   maxZoom: 1e50,
    //   style: [
    //     // the stylesheet for the graph -> not working
    //     {
    //       selector: 'node',
    //       style: {
    //         'background-color': 'red',
    //         color: 'red',
    //         label: 'data(id)'
    //       }
    //     },

    //     {
    //       selector: 'edge',
    //       style: {
    //         width: 3,
    //         'line-color': '#ccc',
    //         'target-arrow-color': '#ccc',
    //         'target-arrow-shape': 'triangle',
    //         'curve-style': 'bezier'
    //       }
    //     }
    //   ],
    //   elements: result,
    //   styleEnabled: true,
    //   layout: { name: 'random' }
    // })

    var options = {
      evtType: "cxttap",
      menuItems: [
        {
          id: "details",
          content: "View Details...",
          tooltipText: "View Details",
          selector: "node, edge",
          onClickFunction: function (event) {

          },
          hasTrailingDivider: true
        },
        {
          id: "generateReport",
          content: "Generate Report",
          selector: "node, edge",
          onClickFunction: function (event) {

          },
          hasTrailingDivider: true
        }
      ],
      menuItemClasses:    ["custom-menu-item", "custom-menu-item:hover"],
      contextMenuClasses: ["custom-context-menu"]
    };

    var cy = cytoscape({
      container: document.getElementById("cy"),

      ready: function () {
        var instance = this.contextMenus(options);

        var api = this.expandCollapse({
          layoutBy: {
            name: "dagre",
            animate: "end",
            randomize: false,
            fit: true,
            nodeDimensionsIncludeLabels: true,
            avoidOverlap: true,
          },
          fisheye: false,
          animate: true,
          undoable: false,
          cueEnabled: true,
          expandCollapseCuePosition: "top-left",
          expandCollapseCueSize: 16,
          expandCollapseCueLineSize: 24,
          expandCueImage: "./static/imgs/ic_expand_more.svg",
          collapseCueImage: "./static/imgs/ic_expand_less.svg",
          expandCollapseCueSensitivity: 1,
          edgeTypeInfo: "edgeType",
          groupEdgesOfSameTypeOnCollapse: false,
          allowNestedEdgeCollapse: true,
          zIndex: 999
        });

        document
          .getElementById("collapseAll")
          .addEventListener("click", function () {
            api.collapseAll();
          });

        document
          .getElementById("expandAll")
          .addEventListener("click", function () {
          api.expandAll();
        });
      },

      style: [
        //CORE
        {
          selector: "core",
          css: {
            "active-bg-size": 0 //The size of the active background indicator.
          }
        },

        //NODE
        {
          selector: "node",
          css: {
            width: "38px",
            height: "38px",
            "font-family": "Nokia Pure Regular",
            "background-opacity": "1"
          }
        },
        //GROUP
        {
          selector: "node.cy-expand-collapse-collapsed-node",
          css: {
            width: "56px",
            height: "56px",
            "border-color": "#8f8b8b",
            "border-width": "1px",
            "background-opacity": "0",
            "background-color": "#8f8b8b",
            "font-family": "Nokia Pure Regular"
          }
        },
        {
          selector: "$node > node",
          css: {
            "background-color": "#fff",
            "background-opacity": "1",
            "border-width": "1px",
            "border-color": "#dcdcdc",

            //LABEL
            //label: "data(name)",
            color: "#000",
            shape: "rectangle",
            "text-opacity": "0.56",
            "font-size": "10px",
            "text-transform": "uppercase",
            "background-color": "#8f8b8b",
            "text-wrap": "none",
            "text-max-width": "75px",
            "padding-top": "16px",
            "padding-left": "16px",
            "padding-bottom": "16px",
            "padding-right": "16px"
          }
        },
        {
          selector: ":parent",
          css: {
            "text-valign": "top",
            "text-halign": "center"
          }
        },
        //EDGE
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "#b8b8b8",
            "curve-style": "bezier",
            'target-arrow-shape': 'triangle',
            //LABEL
            label: "",
            //content: "data(label)"
          }
        },
        {
          selector: "edge.hover",
          style: {
            width: 2,
            "line-color": "#239df9"
          }
        },
        {
          selector: "edge:selected",
          style: {
            width: 1,
            "line-color": "#239df9"
          }
        }
      ],

      layout: {
        name: "dagre",
        padding: 0,
        spacingFactor: 0,
        nodeDimensionsIncludeLabels: true,
        fit: true,
        avoidOverlap: true,
        ranker:"network-simplex"
      },

      elements: data,

      zoomingEnabled: true,
      userZoomingEnabled: true,
      autoungrabify: false
    });


    document
          .getElementById("expandAll").click();

    cy.fit();

    //NODE EVENTS
    cy.on("mouseover", "node", function (e) {
      e.target.addClass("hover");
      var node = e.target;
      let popper = node.popper({
        content: () => {
          let div = document.createElement('div');
      
          div.innerHTML = 'Sticky Popper content';
      
          document.body.appendChild( div );
      
          return div;
        }
      });
      
      let update = () => {
        popper.update();
      };
      
      node.on('position', update);
      
      cy.on('pan zoom resize', update);
    });

    cy.on("mouseout", "node", function (e) {
      e.target.removeClass("hover");
    });

    cy.on("mousedown", "node", function (e) {
      e.target.addClass("hover");
      var node = e.target;
      let popper = node.popper({
        content: () => {
          let div = document.createElement('div');
      
          div.innerHTML = 'Sticky Popper content';
      
          document.body.appendChild( div );
      
          return div;
        }
      });
      
      let update = () => {
        popper.update();
      };
      
      node.on('position', update);
      
      cy.on('pan zoom resize', update);
    });

    cy.on("click", "node", function (e) {
      console.log("clicked:" + this.id());
    });

    //EDGES EVENTS
    cy.on("mouseover", "edge", function (e) {
      e.target.addClass("hover");
      var edge = e.target;
      let popper = edge.popper({
        content: () => {
          let div = document.createElement('div');
      
          div.innerHTML = 'Sticky Popper content';
      
          document.body.appendChild( div );
      
          return div;
        }
      });
      
      let update = () => {
        popper.update();
      };
      
      edge.on('position', update);
      
      cy.on('pan zoom resize', update);
    });
    cy.on("mouseout", "edge", function (e) {
      e.target.removeClass("hover");
    });

    cy.nodeHtmlLabel([
      {
        query: ".groupIcon",
        halign: "center",
        valign: "center",
        halignBox: "center",
        valignBox: "center",
        tpl: function (data) {
          return `<div class="group ${data.collapsedChildren ? "show" : "hide"}">
                    <span class="group-graphic alarmSeverity-${data.alarmSeverity}">
                      <i class="icon icon-group"></i>
                      <span class="overlay"></span>
                    </span> 
                    <span class="group-label">${data.displayName}</span>
                  </div>`;
        }
      },
      {
        query: ".groupIcon.hover",
        halign: "center",
        valign: "center",
        halignBox: "center",
        valignBox: "center",
        tpl: function (data) {
          return `<div class="group ${data.collapsedChildren ? "show" : "hide"}">
                    <span class="group-graphic hover alarmSeverity-${
                      data.alarmSeverity
                    }">
                      <i class="icon icon-group"></i>
                      <span class="overlay"></span>
                    </span>
                    <span class="group-label">${data.displayName}</span>
                  </div>`;
        }
      },
      {
        query: ".groupIcon:selected",
        halign: "center",
        valign: "center",
        halignBox: "center",
        valignBox: "center",
        tpl: function (data) {
          return `<div class="group ${data.collapsedChildren ? "show" : "hide"}">
                    <span class="group-graphic selected alarmSeverity-${
                      data.alarmSeverity
                    }">
                      <i class="icon icon-group"></i>
                      <span class="overlay"></span>
                    </span>
                    <span class="group-label">${data.displayName}</span>
                  </div>`;
        }
      },
      {
        query: ".groupIcon.hover:selected",
        halign: "center",
        valign: "center",
        halignBox: "center",
        valignBox: "center",
        tpl: function (data) {
          return `<div class="group ${data.collapsedChildren ? "show" : "hide"}">
                    <span class="group-graphic hover selected alarmSeverity-${
                      data.alarmSeverity
                    }">
                      <i class="icon icon-group"></i>
                      <span class="overlay"></span>
                    </span>
                    <span class="group-label">${data.displayName}</span>
                  </div>`;
        }
      },
      {
        query: ".nodeIcon",
        halign: "center",
        valign: "center",
        halignBox: "center",
        valignBox: "center",
        tpl: function (data) {
          return `<div class="element ${data._hidden}">
                    <span class="element-severity_badge">
                      <i class="icon icon-${data.alarmSeverity}" /></i>
                    </span>
                    <span class="element-pm_badge">
                      <i class="icon icon-pm" /></i>
                      <span>PM</span>
                    </span>
                    <span class="element-graphic operationalState-${data.operationalState}">
                      <i class="icon icon-${data.kind}" /></i>
                      <span class="overlay"></span>
                    </span>
                    <span title="${data.displayName}" class="element-label">${data.displayName}</span>
                  </div>`;
        }
      },
      {
        query: ".nodeIcon.hover",
        halign: "center",
        valign: "center",
        halignBox: "center",
        valignBox: "center",
        tpl: function (data) {
          return `<div class="element ${data._hidden}">
                    <span class="element-severity_badge">
                      <i class="icon icon-${data.alarmSeverity}" /></i>
                    </span>
                    <span class="element-pm_badge">
                      <i class="icon icon-pm" /></i>
                      <span>PM</span>
                    </span>
                    <span class="element-graphic hover operationalState-${data.operationalState}">
                      <i class="icon icon-${data.kind} icon-hover" /></i>
                      <span class="overlay"></span>
                    </span>
                    <span title="${data.displayName}" class="element-label">${data.displayName}</span>
                  </div>`;
        }
      },
      {
        query: ".nodeIcon:selected",
        halign: "center",
        valign: "center",
        halignBox: "center",
        valignBox: "center",
        tpl: function (data) {
          return `<div class="element ${data._hidden}">
                    <span class="element-severity_badge">
                      <i class="icon icon-${data.alarmSeverity}" /></i>
                    </span>
                    <span class="element-pm_badge">
                      <i class="icon icon-pm" /></i>
                      <span>PM</span>
                    </span>
                    <span class="element-graphic selected operationalState-${data.operationalState}">
                      <i class="icon icon-${data.kind}" /></i>
                      <span class="overlay"></span>  
                    </span>
                    <span title="${data.displayName}" class="element-label">${data.displayName}</span>
                  </div>`;
        }
      },
      {
        query: ".nodeIcon.hover:selected",
        halign: "center",
        valign: "center",
        halignBox: "center",
        valignBox: "center",
        tpl: function (data) {
          return `<div class="element ${data._hidden}">
                    <span class="element-severity_badge">
                      <i class="icon icon-${data.alarmSeverity}" /></i>
                    </span>
                    <span class="element-pm_badge">
                      <i class="icon icon-pm" /></i>
                      <span>PM</span>
                    </span>
                    <span class="element-graphic hover selected operationalState-${data.operationalState}">
                      <i class="icon icon-${data.kind}" /></i>
                      <span class="overlay"></span>
                    </span>
                    <span title="${data.displayName}" class="element-label">${data.displayName}</span>
                  </div>`;
        }
      }
    ]);

    

    cy.nodes().on("expandcollapse.beforecollapse", function (e) {
      console.log("Triggered before a node is collapsed");
    });

    cy.nodes().on("expandcollapse.aftercollapse", function (e) {
      console.log("Triggered after a node is collapsed");
    });

    cy.nodes().on("expandcollapse.beforeexpand", function (e) {
      console.log("Triggered before a node is expanded");
    });

    cy.nodes().on("expandcollapse.afterexpand", function (e) {
      console.log("Triggered after a node is expanded");
    });

    cy.edges().on("expandcollapse.beforecollapseedge", function (e) {
      console.log("Triggered before an edge is collapsed");
    });

    cy.edges().on("expandcollapse.aftercollapseedge", function (e) {
      console.log("Triggered after an edge is collapsed");
    });

    cy.edges().on("expandcollapse.beforeexpandedge", function (e) {
      console.log("Triggered before an edge is expanded");
    });

    cy.edges().on("expandcollapse.afterexpandedge", function (e) {
      console.log("Triggered after an edge is expanded");
    });

    cy.nodes().on("expandcollapse.beforecollapse", function (event) {
      var node = this;
      event.cy
        .nodes()
        .filter((entry) => entry.data().parent === node.id())
        .map((entry) => entry.data("_hidden", "node-hidden"));
      node.data("_hidden", "");
    });

    cy.nodes().on("expandcollapse.afterexpand", function (event) {
      var node = this;
      event.cy
        .nodes()
        .filter((entry) => entry.data().parent === node.id())
        .map((entry) => entry.data("_hidden", ""));
      node.data("_hidden", "node-hidden");
    });

    var defaults = {
      container: false, // html dom element "#cytoscape"
      viewLiveFramerate: 0, // set false to update graph pan only on drag end; set 0 to do it instantly; set a number (frames per second) to update not more than N times per second
      thumbnailEventFramerate: 30, // max thumbnail's updates per second triggered by graph updates
      thumbnailLiveFramerate: false, // max thumbnail's updates per second. Set false to disable
      dblClickDelay: 200, // milliseconds
      removeCustomContainer: false, // destroy the container specified by user on plugin destroy
      rerenderDelay: 100 // ms to throttle rerender updates to the panzoom for performance
    };

    var nav = cy.navigator(defaults);

    //module.exports = { cy, nav };


    console.log(data)
    console.log(data.elements)

    /*cy.style()
                .resetToDefault() // start a fresh default stylesheet

                // and then define new styles
                .selector('node')
                    .style('background-color', 'magenta')

                // ...

                .update() // indicate the end of your new stylesheet so that it can be updated on elements
                ;*/

    var stringStylesheet = `node {
                    content: data(label);
                    text-wrap: wrap;
                    font-size: 14px;
                    text-outline-width: 3px;
                    text-outline-color: #888;
                    text-valign: center;
                    text-halign: center;
                    color: #fc4e03;
                    width: data(width);
                    height: data(height);
                    border-color: #000;
                    shape: data(shape);
                    text-background-opacity: 1;
                    background-color: #888;
                }
                node.non_existing{
                    display: none;
                }
                node.exactly_one  {
                    border-width: 4px;
                    border-style: solid;
                }
                node.at_least_one  {
                    border-width: 8px;
                    border-style: double;
                }
                node.at_most_one  {
                    border-width: 3px;
                    border-style: dotted;
                }
                node.node_unknown {
                    border-width: 0px;
                }
                edge {
                    target-arrow-shape: triangle;
                    target-arrow-fill: filled;
                    source-arrow-fill: filled;
                }
                edge.none_to_none {
                    width: 4px;
                    line-style: dashed;
                    target-arrow-shape: triangle;
                    target-arrow-fill: filled;
                    source-arrow-fill: filled;
                }
                edge.all_to_all {
                    width: 4px;
                    line-style: solid;
                }
                edge.edge_unknown {
                    width: 4px;
                    line-style: dotted;
                }
                edge.total {
                    source-arrow-shape: circle;
                    source-arrow-fill: filled;
                }
                edge.functional {
                    source-arrow-shape: square;
                }
                edge.injective {
                    target-arrow-shape: triangle-backcurve;
                }
                edge.surjective {
                    target-arrow-fill: filled;
                }
                node:selected {
                    overlay-opacity: 0.2;
                }
                edge:selected {
                    overlay-opacity: 0.2;
                }
                :parent {
                    text-valign: top;
                    text-halign: center;
                }
                `
    //cy.style(stringStylesheet)

    var param = {
      name: "dagre",
      animate: "end",
      randomize: false,
      fit: true,
      nodeDimensionsIncludeLabels: true
    }
    var layout = makeLayout()

    // console.log(layout)

    // layout.run()

    var $btnParam = h(
      'div',
      {
        class: 'param'
      },
      []
    )

    var $config = $('#config')

    $config.appendChild($btnParam)

    var sliders = [
      {
        label: 'Edge length',
        param: 'edgeLengthVal',
        min: 1,
        max: 200
      },

      {
        label: 'Node spacing',
        param: 'nodeSpacing',
        min: 1,
        max: 50
      }
    ]

    var buttons = [
      {
        label: h('span', { class: 'fa fa-random' }, []),
        layoutOpts: {
          randomize: true,
          flow: null
        }
      },
      {
        label: h('span', { class: 'fa fa-long-arrow-down' }, []),
        layoutOpts: {
          flow: { axis: 'y', minSeparation: 30 }
        }
      },
      {
        label: h('span', { class: 'fa fa-eye' }, []),
        new_style:  [
          //CORE
          {
            selector: "core",
            css: {
              "active-bg-size": 0 //The size of the active background indicator.
            }
          },
  
          //NODE
          {
            selector: "node",
            css: {
              width: "38px",
              height: "38px",
              "font-family": "Nokia Pure Regular",
              "background-opacity": "1"
            }
          },
          //GROUP
          {
            selector: "node.cy-expand-collapse-collapsed-node",
            css: {
              width: "56px",
              height: "56px",
              "border-color": "#8f8b8b",
              "border-width": "1px",
              "background-opacity": "0",
              "background-color": "#8f8b8b",
              "font-family": "Nokia Pure Regular"
            }
          },
          {
            selector: "$node > node",
            css: {
              "background-color": "#fff",
              "background-opacity": "1",
              "border-width": "1px",
              "border-color": "#dcdcdc",
  
              //LABEL
              //label: "data(name)",
              color: "#000",
              shape: "rectangle",
              "text-opacity": "0.56",
              "font-size": "10px",
              "text-transform": "uppercase",
              "background-color": "#8f8b8b",
              "text-wrap": "none",
              "text-max-width": "75px",
              "padding-top": "16px",
              "padding-left": "16px",
              "padding-bottom": "16px",
              "padding-right": "16px"
            }
          },
          {
            selector: ":parent",
            css: {
              "text-valign": "top",
              "text-halign": "center"
            }
          },
          //EDGE
          {
            selector: "edge",
            style: {
              width: 1,
              "line-color": "#b8b8b8",
              "curve-style": "bezier",
              'target-arrow-shape': 'triangle',
              content: "data(label)"
              //LABEL
              //label: ""
            }
          },
          {
            selector: "edge.hover",
            style: {
              width: 2,
              "line-color": "#239df9"
            }
          },
          {
            selector: "edge:selected",
            style: {
              width: 1,
              "line-color": "#239df9"
            }
          }
        ]
      },
      {
        label: h('span', { class: 'fa fa-eye-slash' }, []),
        new_style:  [
          //CORE
          {
            selector: "core",
            css: {
              "active-bg-size": 0 //The size of the active background indicator.
            }
          },
  
          //NODE
          {
            selector: "node",
            css: {
              width: "38px",
              height: "38px",
              "font-family": "Nokia Pure Regular",
              "background-opacity": "1"
            }
          },
          //GROUP
          {
            selector: "node.cy-expand-collapse-collapsed-node",
            css: {
              width: "56px",
              height: "56px",
              "border-color": "#8f8b8b",
              "border-width": "1px",
              "background-opacity": "0",
              "background-color": "#8f8b8b",
              "font-family": "Nokia Pure Regular"
            }
          },
          {
            selector: "$node > node",
            css: {
              "background-color": "#fff",
              "background-opacity": "1",
              "border-width": "1px",
              "border-color": "#dcdcdc",
  
              //LABEL
              //label: "data(name)",
              color: "#000",
              shape: "rectangle",
              "text-opacity": "0.56",
              "font-size": "10px",
              "text-transform": "uppercase",
              "background-color": "#8f8b8b",
              "text-wrap": "none",
              "text-max-width": "75px",
              "padding-top": "16px",
              "padding-left": "16px",
              "padding-bottom": "16px",
              "padding-right": "16px"
            }
          },
          {
            selector: ":parent",
            css: {
              "text-valign": "top",
              "text-halign": "center"
            }
          },
          //EDGE
          {
            selector: "edge",
            style: {
              width: 1,
              "line-color": "#b8b8b8",
              "curve-style": "bezier",
              'target-arrow-shape': 'triangle',
              //LABEL
              label: ""
            }
          },
          {
            selector: "edge.hover",
            style: {
              width: 2,
              "line-color": "#239df9"
            }
          },
          {
            selector: "edge:selected",
            style: {
              width: 1,
              "line-color": "#239df9"
            }
          }
        ]
      }
    ]

    sliders.forEach(makeSlider)

    buttons.forEach(makeButton)

    function makeLayout(opts) {
      param.randomize = false
      param.edgeLength = function (e) {
        return param.edgeLengthVal / e.data('weight')
      }

      for (var i in opts) {
        param[i] = opts[i]
      }

      return cy.layout(param)
    }

    function makeSlider(opts) {
      var $input = h(
        'input',
        {
          id: 'slider-' + opts.param,
          type: 'range',
          min: opts.min,
          max: opts.max,
          step: 1,
          value: param[opts.param],
          class: 'slider'
        },
        []
      )

      var $param = h('div', { class: 'param' }, [])

      var $label = h('label', { class: 'label label-default', for: 'slider-' + opts.param }, [t(opts.label)])

      $param.appendChild($label)
      $param.appendChild($input)

      $config.appendChild($param)

      var update = _.throttle(function () {
        param[opts.param] = $input.value

        layout.stop()
        layout = makeLayout()
        layout.run()
      }, 1000 / 30)

      $input.addEventListener('input', update)
      $input.addEventListener('change', update)
    }

    function makeButton(opts) {
      var $button = h('button', { class: 'btn btn-default' }, [opts.label])

      $btnParam.appendChild($button)

      $button.addEventListener('click', function () {
        layout.stop()

        if (opts.fn) {
          opts.fn()
        }
        
        if(opts.layoutOpts) {
          layout = makeLayout(opts.layoutOpts)
          layout.run()
        }
        
        if(opts.new_style)
          cy.style(opts.new_style)
   
      })
    }
  },
  'json'
)

