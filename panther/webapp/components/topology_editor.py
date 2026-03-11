"""TopologyEditor — Placeholder for visual experiment topology component.

This module is the student's core thesis contribution. The student evaluates
at least 3 visualization approaches and implements the topology editor:

1. **vis.js Network** — JS graph library with built-in physics and manipulation
   API. Requires CDN + JavaScript bridge via ``ui.run_javascript()``.
2. **React Flow** — React-based node editor. Requires npm build step +
   iframe/webcomponent embedding in NiceGUI.
3. **NiceGUI Native** — Pure SVG/ECharts approach using only NiceGUI built-in
   capabilities (``ui.html()``, ``ui.echart()``, ``ui.element()``). Zero
   external deps but requires custom drag-and-drop implementation.

The evaluation criteria and final recommendation are the student's to define.

See ``ARCHITECTURE.md`` § "Visual Topology Editor" for graph-relevant config
fields and § "Config Model Hierarchy" for the data model.
"""
