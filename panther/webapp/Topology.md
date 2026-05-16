# PANTHER Topology Diagram Viewer

Native NiceGUI implementation for visualizing experiment configuration topologies.

---

## 🏗️ Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│                     Topology Page                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Config Selector                                   │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Info Panel (test count, services, network type)    │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Topology Card                                      │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │  View Mode Toggle                            │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │  Statistics Chips                            │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │  Network Environment Badges                  │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │  Legend                                      │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  │  ┌───────────────────────────────────────────────┐  │  │
│  │  │  ECharts Graph Component                     │  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## 📦 Components

### 1. `panther/webapp/pages/topology.py`
**Main page entry point**
- Config file selector dropdown
- Loaded configuration details panel
- Diagram area container
- Refresh button handlers
- Config loading and validation

### 2. `panther/webapp/services/topology_service.py`
**Data transformation service**
- Converts raw YAML config into graph model
- Service deduplication across tests
- Connection frequency counting
- Auto-scaling calculation based on node count
- Color coding and shape mapping
- Singleton factory pattern for API endpoints

### 3. `panther/webapp/components/topology/topology_renderer.py`
**ECharts visualization renderer**
- View mode selector (Aggregated / Per Test)
- Statistics display
- Network environment badges
- Legend rendering
- ECharts force-directed graph configuration
- Interaction handlers (click, hover, drag)

### 4. `panther/webapp/api/topology_api.py`
**REST API endpoints**
- `/api/topology/configs` - list available config files
- `/api/topology/config/{filename}` - get graph data
- `/api/topology/config/{filename}/raw` - get raw config

---

## Core Features

### Aggregated View (Default)
-Shows **all unique services** across all tests in the config
-Each node displays usage count `× N`
-Edge thickness indicates how many times that connection is used
-All network environments used in the config are shown
-No duplicate services - every service appears exactly once

### Per Test View
-Original individual test diagrams
-Tabbed interface for switching between tests
-Shows exact 2-service topology for each test
-Displays execution environment badges

### Visual Features
| Feature | Details |
|---|---|
| **Color Coding** | 🟢 Green = IUT (Implementation Under Test)<br>🔵 Blue = TESTER |
| **Shapes** | ● Circle = Server<br>▭ Rounded Rectangle = Client |
| **Node Size** | Calculated automatically based on number of ports |
| **Scaling** | Auto-adjusts font size, node size, spacing for 2-20+ services |
| **Interactions** | Drag nodes freely<br>Mouse wheel zoom<br>Pan canvas<br>Click for node details |
| **Edges** | Arrow direction shows client → server flow<br>Protocol name label on edge |

### Statistics Panel
-Total number of tests in config
-Unique services count
-Unique connections count

---

## Implementation Details

### Technology Stack
- **100% Native NiceGUI** - No external dependencies, no CDNs
- **Apache ECharts** - Included natively in NiceGUI
- **Force Directed Layout** - Automatic node positioning
- **No Javascript required** - All configuration in Python

### Scalability
| Config Size | Adaptations |
|---|---|
| 2-4 services | Large nodes, full labels, edges with labels |
| 5-8 services | Medium nodes, standard font size |
| 9-12 services | Reduced node size, smaller font |
| 13+ services | Compact mode, minimal labels |

### Performance
-Layout calculations run in Python
-All rendering happens client-side in browser
-Smooth animations for layout updates
-Works with very large config files

---

## 🔧 Usage

1. Start the webapp:
   ```bash
   panther web
   ```

2. Navigate to **Topology** page

3. Select any experiment config file from the dropdown

4. Toggle between view modes:
   - **Full Config Overview** - See the big picture across all tests
   - **Per Test View** - Drill down into individual test topologies

5. Interact with the diagram:
   - Drag nodes to reposition them
   - Scroll mouse wheel to zoom
   - Click and drag background to pan
   - Hover over nodes for full details

---

## Design Principles

1. **Zero External Dependencies** - Only use NiceGUI built-in capabilities
2. **Graceful Degradation** - Works for any config size
3. **Information Density** - Show as much useful information as possible without clutter
4. **Intuitive Navigation** - Users can switch between overview and detail views
5. **Performance First** - Smooth interaction even with large configs

---

## 📌 Data Model

### Node Structure
```python
{
  "id": "service_identifier",
  "name": "Display Name",
  "category": "IUT" | "TESTERS",
  "role": "server" | "client",
  "protocol": "quic",
  "protocol_version": "rfc9000",
  "test_count": 8,
  "ports": ["4443:4443", ...],
  "has_certificates": true,
  "networks": ["docker_compose", "shadow_ns"],
  "execution_envs": ["strace", "gperf_cpu"]
}
```

### Edge Structure
```python
{
  "source": "client_service",
  "target": "server_service",
  "protocol": "quic",
  "count": 5,
  "lineStyle": { "width": 4 },
  "label": "QUIC"
}
```

---

## API Reference

### `TopologyService` Class
`panther/webapp/services/topology_service.py`

| Method | Description |
|---|---|
| `parse_config_to_graph(config)` | Main entry point. Converts raw config dict to complete graph structure including both individual tests and aggregated view |
| `_create_aggregated_view(all_tests)` | Deduplicates services and connections across all tests. Calculates usage counts and frequency metrics |
| `_parse_single_test(test, test_index)` | Parses individual test case into nodes and edges |
| `_create_node(service_id, service_data)` | Creates standardized node structure with all properties |
| `_extract_connections(services)` | Finds all connections between services based on `target` references |
| `_create_network_group(network_env)` | Extracts network environment metadata |
| `_calculate_node_size(service_data)` | Calculates node visual size based on port count |
| `_build_node_tooltip(service_id, data)` | Generates HTML tooltip content |
| `get_scaling_factors(node_count)` | Returns adaptive scaling parameters based on total number of nodes |
| `get_topology_service()` | Singleton factory function for API usage |

---

### `TopologyRenderer` Class
`panther/webapp/components/topology/topology_renderer.py`

| Method | Description |
|---|---|
| `render(config)` | Main render entry point. Builds complete UI with view mode toggle, statistics and diagram |
| `_render_test_diagram(test_data, is_aggregated)` | Renders single diagram view. Handles both aggregated and per-test modes |
| `_build_echarts_options(test_data, scaling)` | Constructs full ECharts configuration object |
| `_on_node_click(event)` | Node click event handler with safe event parsing |
| `_on_test_change(event)` | Tab switch event handler |
| `export_svg()` | SVG export placeholder |

---

### Page Methods
`panther/webapp/pages/topology.py`

| Function | Description |
|---|---|
| `content()` | Page entry point called by NiceGUI router |
| `select_config(path)` | Config selection handler. Loads config, updates info panel and renders diagram |
| `refresh_config_list()` | Reloads available config files list |
| `refresh_diagram()` | Re-renders currently loaded diagram |

---

## Future Enhancements

- [ ] SVG / PNG export
- [ ] Test filtering checkboxes
- [ ] Highlight on hover which tests use selected node
- [ ] Network environment clustering
- [ ] Execution environment filtering
- [ ] Right click context menus
- [ ] Live status indicators for running experiments
