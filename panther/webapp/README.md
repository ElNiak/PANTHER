# Web Application Interface — PANTHER Dashboard & APIs 🌐

> **⚠️ DISCLAIMER: This documentation is currently under development and not yet complete. Features described may be partially implemented or planned for future releases. Check back for updates as we continue to improve the web application interface.**


> **Purpose:** Complete guide to PANTHER's web interface for experiment management, result visualization, and real-time monitoring
> **Target:** Users wanting to design experiments graphically; researchers analyzing results; teams needing collaborative experiment management
> **Technology:** Flask-based web application with Bootstrap UI, Chart.js visualizations, and RESTful APIs

PANTHER provides a **comprehensive web interface** that allows you to design, execute, monitor, and analyze experiments through an intuitive dashboard. The web application complements the CLI tools with visual experiment creation, real-time monitoring, and interactive result analysis.

---

## Web Application Architecture

### Core Components

1. **Experiment Designer**: Visual interface for creating test configurations
2. **Real-time Monitor**: Live experiment execution tracking with progress indicators
3. **Results Dashboard**: Interactive data visualization and analysis tools
4. **API Gateway**: RESTful endpoints for programmatic access
5. **Static Analysis**: Embedded tools for packet capture analysis and formal verification results

### Technology Stack

- **Backend**: Flask web framework with CORS support
- **Frontend**: Bootstrap 5 for responsive UI design
- **Visualization**: Chart.js for interactive charts and graphs
- **Data Processing**: Pandas for result analysis and CSV generation
- **Real-time Updates**: WebSocket support for live monitoring
- **File Handling**: Support for PCAP analysis, log viewing, and result downloads

---

## Starting the Web Application

### Command Line Launch
```bash
# Start web interface with default configuration
panther --web --experiment-config experiment_config.yaml

# Start with custom port and host
panther --web --host 0.0.0.0 --port 8080 --experiment-config config.yaml

# Enable debug mode for development
panther --web --debug --experiment-config config.yaml
```

### Configuration Options
```yaml
# In your experiment configuration
webapp:
  host: "0.0.0.0"
  port: 8080
  debug: false
  secret_key: "your-secret-key"
  session_timeout: 3600
  cors_origins: ["*"]
```

### Access URLs
- **Main Dashboard**: `http://localhost:8080/`
- **API Documentation**: `http://localhost:8080/api/docs`
- **Results Browser**: `http://localhost:8080/results`
- **Experiment Creator**: `http://localhost:8080/creator`

---

## Main Dashboard Interface

### Navigation Structure

```
┌─ PANTHER Dashboard ──────────────────────────────────┐
├─ 🏠 Home                                            │
├─ ⚙️  Experiment Creator                              │
├─ 📊 Results                                         │
├─ 📈 Global Analysis                                 │
├─ 🔧 Configuration                                   │
└─ 📚 Documentation                                   │
```

### Home Page Features

#### Current Experiment Status
- **Progress Indicators**: Visual progress bars for running experiments
- **Test Queue**: List of pending and active tests
- **Resource Usage**: CPU, memory, and container status
- **Recent Results**: Quick access to latest experiment outputs

#### Quick Actions
```html
<!-- Example UI Elements -->
<div class="quick-actions">
    <button class="btn btn-primary" onclick="startExperiment()">
        🚀 Start New Experiment
    </button>
    <button class="btn btn-info" onclick="viewResults()">
        📊 View Results
    </button>
    <button class="btn btn-success" onclick="exportData()">
        💾 Export Data
    </button>
</div>
```

#### Protocol Selection
- **Dynamic Protocol Menu**: Automatically populated from available plugins
- **Implementation Matrix**: Shows available IUT implementations for each protocol
- **Compatibility Check**: Validates implementation combinations

---

## Experiment Creator Interface

### Visual Configuration Builder

The experiment creator provides a **drag-and-drop interface** for building test configurations:

#### Service Configuration Panel
```html
<!-- Service Configuration Example -->
<div class="service-config">
    <h3>📦 Services Configuration</h3>

    <!-- IUT Services -->
    <div class="card-group">
        <div class="card">
            <div class="card-body">
                <h5>QUIC Server</h5>
                <select name="implementation">
                    <option value="quiche">Quiche</option>
                    <option value="picoquic">Picoquic</option>
                    <option value="aioquic">Aioquic</option>
                    <option value="quinn">Quinn</option>
                </select>

                <div class="port-config">
                    <label>Port:</label>
                    <input type="number" value="4433" min="1024" max="65535">
                </div>

                <div class="protocol-config">
                    <label>ALPN:</label>
                    <input type="text" value="h3,hq-29" placeholder="Protocol identifiers">
                </div>
            </div>
        </div>
    </div>

    <!-- Tester Services -->
    <div class="card-group">
        <div class="card">
            <div class="card-body">
                <h5>🧪 Formal Verifier</h5>
                <select name="tester">
                    <option value="panther_ivy">Panther Ivy</option>
                    <option value="custom_tester">Custom Tester</option>
                </select>

                <div class="test-config">
                    <label>Test Suite:</label>
                    <select name="test_suite">
                        <option value="basic_conformance">Basic Conformance</option>
                        <option value="advanced_security">Advanced Security</option>
                        <option value="performance_stress">Performance Stress</option>
                    </select>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### Environment Configuration
```html
<div class="environment-config">
    <h3>🌐 Environment Setup</h3>

    <!-- Network Environment -->
    <div class="network-env">
        <h4>Network Environment</h4>
        <div class="form-check">
            <input type="radio" name="network_env" value="docker_compose" checked>
            <label>Docker Compose</label>
        </div>
        <div class="form-check">
            <input type="radio" name="network_env" value="localhost">
            <label>Localhost</label>
        </div>
        <div class="form-check">
            <input type="radio" name="network_env" value="shadow">
            <label>Shadow Simulator</label>
        </div>
    </div>

    <!-- Execution Environment -->
    <div class="exec-env">
        <h4>Execution Environment</h4>
        <select name="exec_env">
            <option value="docker_container">Docker Container</option>
            <option value="host">Host System</option>
        </select>
    </div>
</div>
```

#### Dynamic Form Generation

The creator automatically generates forms based on plugin schemas:

```javascript
// Dynamic form generation based on plugin configuration
function generatePluginForm(pluginConfig) {
    const formContainer = document.getElementById('plugin-config');

    // Generate form fields based on schema
    for (const [fieldName, fieldConfig] of Object.entries(pluginConfig.schema)) {
        const fieldElement = createFormField(fieldName, fieldConfig);
        formContainer.appendChild(fieldElement);
    }
}

function createFormField(name, config) {
    const field = document.createElement('div');
    field.className = 'form-group';

    // Field type-specific rendering
    switch (config.type) {
        case 'string':
            field.innerHTML = `
                <label for="${name}">${config.label}</label>
                <input type="text" id="${name}" name="${name}"
                       value="${config.default || ''}"
                       class="form-control">
                <small class="form-text text-muted">${config.help}</small>
            `;
            break;
        case 'integer':
            field.innerHTML = `
                <label for="${name}">${config.label}</label>
                <input type="range" id="${name}" name="${name}"
                       min="${config.min || 0}" max="${config.max || 100}"
                       value="${config.default || 50}"
                       class="form-range">
                <output>${config.default || 50}</output>
            `;
            break;
        case 'boolean':
            field.innerHTML = `
                <div class="form-check">
                    <input type="checkbox" id="${name}" name="${name}"
                           ${config.default ? 'checked' : ''}
                           class="form-check-input">
                    <label for="${name}" class="form-check-label">${config.label}</label>
                </div>
            `;
            break;
        case 'enum':
            const options = config.choices.map(choice =>
                `<option value="${choice}" ${choice === config.default ? 'selected' : ''}>${choice}</option>`
            ).join('');
            field.innerHTML = `
                <label for="${name}">${config.label}</label>
                <select id="${name}" name="${name}" class="form-select">
                    ${options}
                </select>
            `;
            break;
    }

    return field;
}
```

### Configuration Validation

Real-time validation as users build configurations:

```javascript
// Real-time configuration validation
function validateConfiguration() {
    const config = gatherFormData();

    fetch('/api/validate-config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.valid) {
            showValidationSuccess();
            enableStartButton();
        } else {
            showValidationErrors(data.errors);
            disableStartButton();
        }
    });
}

function showValidationErrors(errors) {
    const errorContainer = document.getElementById('validation-errors');
    errorContainer.innerHTML = errors.map(error =>
        `<div class="alert alert-danger">${error.field}: ${error.message}</div>`
    ).join('');
}
```

### Configuration Export

Export created configurations in multiple formats:

```html
<div class="export-options">
    <h4>💾 Export Configuration</h4>
    <div class="btn-group">
        <button class="btn btn-primary" onclick="exportYAML()">
            📄 Export YAML
        </button>
        <button class="btn btn-info" onclick="exportJSON()">
            🔧 Export JSON
        </button>
        <button class="btn btn-success" onclick="saveTemplate()">
            📋 Save as Template
        </button>
    </div>
</div>
```

---

## Real-time Experiment Monitoring

### Live Execution Dashboard

#### Progress Tracking
```html
<div class="experiment-monitor">
    <h2>🔄 Experiment: {{ experiment_name }}</h2>

    <!-- Overall Progress -->
    <div class="progress mb-3">
        <div class="progress-bar progress-bar-animated"
             style="width: {{ progress_percentage }}%">
            {{ progress_percentage }}% Complete
        </div>
    </div>

    <!-- Individual Test Progress -->
    <div class="test-progress">
        {% for test in test_cases %}
        <div class="card mb-2">
            <div class="card-body">
                <h5>{{ test.name }}</h5>
                <div class="progress">
                    <div class="progress-bar bg-{{ test.status_color }}"
                         style="width: {{ test.progress }}%">
                        {{ test.status }}
                    </div>
                </div>
                <small class="text-muted">
                    Started: {{ test.start_time }} |
                    Duration: {{ test.elapsed_time }}
                </small>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
```

#### Resource Monitoring
```html
<div class="resource-monitor">
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>💻 CPU Usage</h5>
                    <canvas id="cpuChart"></canvas>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5>💾 Memory Usage</h5>
                    <canvas id="memoryChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <div class="container-status">
        <h5>🐳 Container Status</h5>
        <table class="table">
            <thead>
                <tr>
                    <th>Container</th>
                    <th>Status</th>
                    <th>CPU</th>
                    <th>Memory</th>
                    <th>Network</th>
                </tr>
            </thead>
            <tbody id="container-status-table">
                <!-- Dynamically populated -->
            </tbody>
        </table>
    </div>
</div>
```

#### Live Log Streaming
```html
<div class="log-viewer">
    <h4>📋 Live Logs</h4>
    <div class="log-controls">
        <select id="log-source">
            <option value="all">All Services</option>
            <option value="quic_server">QUIC Server</option>
            <option value="quic_client">QUIC Client</option>
            <option value="ivy_verifier">Ivy Verifier</option>
        </select>
        <select id="log-level">
            <option value="all">All Levels</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
        </select>
        <button onclick="clearLogs()">Clear</button>
        <button onclick="downloadLogs()">Download</button>
    </div>

    <div id="log-output" class="log-output">
        <!-- Live log content -->
    </div>
</div>

<script>
// WebSocket connection for live logs
const logSocket = new WebSocket('ws://localhost:8080/ws/logs');

logSocket.onmessage = function(event) {
    const logData = JSON.parse(event.data);
    appendLogEntry(logData);
};

function appendLogEntry(logData) {
    const logOutput = document.getElementById('log-output');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${logData.level}`;
    logEntry.innerHTML = `
        <span class="log-timestamp">${logData.timestamp}</span>
        <span class="log-source">[${logData.source}]</span>
        <span class="log-level">${logData.level.toUpperCase()}</span>
        <span class="log-message">${logData.message}</span>
    `;
    logOutput.appendChild(logEntry);
    logOutput.scrollTop = logOutput.scrollHeight;
}
</script>
```

---

## Results Analysis Dashboard

### Interactive Data Visualization

#### Test Results Overview
```html
<div class="results-dashboard">
    <h1>📊 QUIC Test Results</h1>

    <!-- Filter Controls -->
    <div class="filter-panel">
        <div class="row">
            <div class="col-md-3">
                <label>Implementation:</label>
                <select id="impl-filter" multiple>
                    <option value="quiche">Quiche</option>
                    <option value="picoquic">Picoquic</option>
                    <option value="aioquic">Aioquic</option>
                    <option value="quinn">Quinn</option>
                </select>
            </div>
            <div class="col-md-3">
                <label>Test Type:</label>
                <div class="form-check">
                    <input type="radio" name="test_type" value="client" id="client">
                    <label for="client">Client</label>
                </div>
                <div class="form-check">
                    <input type="radio" name="test_type" value="server" id="server">
                    <label for="server">Server</label>
                </div>
                <div class="form-check">
                    <input type="radio" name="test_type" value="all" id="all" checked>
                    <label for="all">All</label>
                </div>
            </div>
            <div class="col-md-3">
                <label>Date Range:</label>
                <input type="date" id="start-date">
                <input type="date" id="end-date">
            </div>
            <div class="col-md-3">
                <button class="btn btn-primary" onclick="applyFilters()">
                    🔍 Filter Results
                </button>
            </div>
        </div>
    </div>

    <!-- Charts and Visualizations -->
    <div class="visualization-grid">
        <div class="row">
            <div class="col-xl-4">
                <div class="card">
                    <div class="card-header">
                        📈 Test Success Rate
                    </div>
                    <div class="card-body">
                        <canvas id="successRateChart"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-xl-4">
                <div class="card">
                    <div class="card-header">
                        🕒 Execution Times
                    </div>
                    <div class="card-body">
                        <canvas id="executionTimeChart"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-xl-4">
                <div class="card">
                    <div class="card-header">
                        📦 Packet Statistics
                    </div>
                    <div class="card-body">
                        <canvas id="packetStatsChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### Detailed Test Results Table
```html
<div class="results-table">
    <h3>📋 Detailed Results</h3>
    <table id="resultsDataTable" class="table table-striped">
        <thead>
            <tr>
                <th>Test Name</th>
                <th>Date</th>
                <th>Implementation</th>
                <th>Version</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Packets</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for result in test_results %}
            <tr>
                <td>{{ result.test_name }}</td>
                <td>{{ result.date }}</td>
                <td>{{ result.implementation }}</td>
                <td>{{ result.version }}</td>
                <td>
                    <span class="badge bg-{{ result.status_color }}">
                        {{ result.status }}
                    </span>
                </td>
                <td>{{ result.duration }}</td>
                <td>{{ result.packet_count }}</td>
                <td>
                    <button class="btn btn-sm btn-info"
                            onclick="viewDetails('{{ result.id }}')">
                        👁️ View
                    </button>
                    <button class="btn btn-sm btn-success"
                            onclick="downloadResult('{{ result.id }}')">
                        💾 Download
                    </button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

### Embedded Analysis Tools

#### PCAP Analysis Integration
```html
<div class="pcap-analysis">
    <h4>📡 Packet Capture Analysis</h4>

    <!-- Embedded Wireshark-like viewer -->
    <iframe class="pcap-frame"
            src="{{ pcap_analyzer_url }}#/stats"
            style="width: 100%; height: 500px"
            title="PCAP Analysis">
    </iframe>

    <!-- Quick Statistics -->
    <div class="pcap-stats">
        <div class="row">
            <div class="col-md-3">
                <div class="stat-card">
                    <h5>Total Packets</h5>
                    <span class="stat-value">{{ total_packets }}</span>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <h5>QUIC Packets</h5>
                    <span class="stat-value">{{ quic_packets }}</span>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <h5>Handshake Duration</h5>
                    <span class="stat-value">{{ handshake_duration }}ms</span>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <h5>Data Transfer Rate</h5>
                    <span class="stat-value">{{ transfer_rate }} Mbps</span>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### Formal Verification Results
```html
<div class="ivy-results">
    <h4>🔍 Formal Verification Results</h4>

    <div class="verification-summary">
        <div class="alert alert-{{ verification_status_color }}">
            <h5>Verification Status: {{ verification_status }}</h5>
            <p>{{ verification_summary }}</p>
        </div>
    </div>

    <!-- Property Check Results -->
    <div class="property-results">
        <h5>Property Verification Results</h5>
        <table class="table">
            <thead>
                <tr>
                    <th>Property</th>
                    <th>Status</th>
                    <th>Counterexample</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {% for property in verification_properties %}
                <tr>
                    <td>{{ property.name }}</td>
                    <td>
                        <span class="badge bg-{{ property.status_color }}">
                            {{ property.status }}
                        </span>
                    </td>
                    <td>
                        {% if property.counterexample %}
                        <button class="btn btn-sm btn-warning"
                                onclick="showCounterexample('{{ property.id }}')">
                            ⚠️ View
                        </button>
                        {% else %}
                        N/A
                        {% endif %}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-info"
                                onclick="showPropertyDetails('{{ property.id }}')">
                            📋 Details
                        </button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Trace Visualization -->
    <div class="trace-viewer">
        <h5>Execution Trace</h5>
        <div id="trace-container">
            <!-- Interactive trace visualization -->
        </div>
    </div>
</div>
```

---

## RESTful API Endpoints

### Experiment Management APIs

#### Get Available Plugins
```http
GET /api/plugins
```
**Response:**
```json
{
    "iut_implementations": [
        {"name": "quiche", "protocols": ["quic"], "roles": ["client", "server"]},
        {"name": "picoquic", "protocols": ["quic"], "roles": ["client", "server"]},
        {"name": "aioquic", "protocols": ["quic", "http3"], "roles": ["client", "server"]}
    ],
    "testers": [
        {"name": "panther_ivy", "protocols": ["quic", "minip"], "capabilities": ["formal_verification"]}
    ],
    "environments": {
        "network": ["docker_compose", "localhost_single_container", "shadow"],
        "execution": ["docker_container", "host"]
    }
}
```

#### Create Experiment Configuration
```http
POST /api/experiments
Content-Type: application/json

{
    "name": "my_experiment",
    "network_environment": {
        "type": "docker_compose"
    },
    "services": [
        {
            "name": "quic_server",
            "type": "iut",
            "implementation": "quiche",
            "role": "server",
            "config": {
                "network": {"port": 4433},
                "protocol": {"alpn": ["h3"]}
            }
        }
    ]
}
```

#### Run Experiment
```http
POST /api/run-experiment
Content-Type: application/json

{
    "experiment_id": "exp_123",
    "test_name": "quic_basic_test"  // Optional: run specific test
}
```

#### Get Experiment Status
```http
GET /api/experiments/{experiment_id}/status
```
**Response:**
```json
{
    "experiment_id": "exp_123",
    "status": "running",
    "progress": 65,
    "tests": [
        {
            "name": "quic_basic_test",
            "status": "completed",
            "result": "passed",
            "duration": 45.2
        },
        {
            "name": "quic_stress_test",
            "status": "running",
            "progress": 30,
            "estimated_completion": "2024-01-15T14:30:00Z"
        }
    ]
}
```

### Results API

#### Get Test Results
```http
GET /api/results?implementation=quiche&start_date=2024-01-01&end_date=2024-01-31
```

#### Download Result Data
```http
GET /api/results/{result_id}/download?format=csv
```

#### Get Result Summary
```http
GET /api/results/{result_id}/summary
```
**Response:**
```json
{
    "result_id": "result_456",
    "test_name": "quic_interop_test",
    "implementation": "quiche",
    "status": "passed",
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T10:05:30Z",
    "duration": 330,
    "metrics": {
        "packets_sent": 1247,
        "packets_received": 1245,
        "handshake_time": 128,
        "throughput_mbps": 45.6
    },
    "files": {
        "pcap": "/results/result_456/capture.pcap",
        "logs": "/results/result_456/logs/",
        "ivy_trace": "/results/result_456/ivy/trace.txt"
    }
}
```

### Configuration API

#### Validate Configuration
```http
POST /api/validate-config
Content-Type: application/json

{
    "configuration": { /* YAML configuration as JSON */ }
}
```

#### Get Plugin Schema
```http
GET /api/plugins/{plugin_name}/schema
```

---

## WebSocket Events

### Real-time Updates

#### Experiment Progress
```javascript
// Subscribe to experiment updates
const experimentSocket = new WebSocket('ws://localhost:8080/ws/experiments');

experimentSocket.onmessage = function(event) {
    const update = JSON.parse(event.data);

    switch(update.type) {
        case 'experiment_started':
            updateExperimentStatus(update.experiment_id, 'running');
            break;
        case 'test_completed':
            updateTestResult(update.test_name, update.result);
            break;
        case 'experiment_completed':
            updateExperimentStatus(update.experiment_id, 'completed');
            break;
        case 'error':
            showError(update.message);
            break;
    }
};
```

#### Live Log Streaming
```javascript
// Subscribe to log updates
const logSocket = new WebSocket('ws://localhost:8080/ws/logs');

logSocket.onmessage = function(event) {
    const logEntry = JSON.parse(event.data);
    appendLogToViewer(logEntry);
};
```

---

## Advanced Features

### Custom Dashboards

Create custom analysis dashboards using the widget system:

```html
<div class="custom-dashboard">
    <div class="widget-container">
        <div class="widget" data-widget="test-success-rate">
            <!-- Auto-generated success rate chart -->
        </div>
        <div class="widget" data-widget="performance-trends">
            <!-- Performance trends over time -->
        </div>
        <div class="widget" data-widget="implementation-comparison">
            <!-- Implementation comparison matrix -->
        </div>
    </div>
</div>

<script>
// Initialize custom widgets
document.querySelectorAll('.widget').forEach(widget => {
    const widgetType = widget.dataset.widget;
    initializeWidget(widget, widgetType);
});
</script>
```

### Integration with External Tools

#### Jupyter Notebook Integration
```python
# Access PANTHER results in Jupyter notebooks
import pandas as pd
import requests

# Fetch results via API
response = requests.get('http://localhost:8080/api/results/export?format=csv')
df = pd.read_csv(response.content)

# Analyze results
success_rate = df.groupby('implementation')['status'].apply(lambda x: (x == 'passed').mean())
print(success_rate)
```

#### CI/CD Integration
```yaml
# GitHub Actions example
name: QUIC Protocol Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run PANTHER Tests
        run: |
          panther --web --experiment-config quic_tests.yaml &
          # Wait for web interface to start
          sleep 10
          # Trigger test via API
          curl -X POST http://localhost:8080/api/run-experiment \
               -H "Content-Type: application/json" \
               -d '{"test_name": "quic_conformance"}'
      - name: Collect Results
        run: |
          curl http://localhost:8080/api/results/latest/download?format=junit > results.xml
```

---

## Security and Access Control

### Authentication and Authorization
```yaml
# Security configuration
security:
  enable_auth: true
  auth_method: "jwt"  # or "basic", "oauth"
  session_timeout: 3600
  cors_origins: ["https://trusted-domain.com"]
  api_rate_limit: 100  # requests per minute
```

### HTTPS Configuration
```yaml
# HTTPS setup
server:
  ssl:
    enabled: true
    cert_file: "/certs/server.crt"
    key_file: "/certs/server.key"
    ca_file: "/certs/ca.crt"
```

---

## Troubleshooting

### Common Issues

**Web Interface Not Starting:**
```bash
# Check if port is in use
netstat -tulpn | grep :8080

# Check Flask debug output
panther --web --debug --experiment-config config.yaml
```

**WebSocket Connection Issues:**
```javascript
// Check WebSocket status
if (socket.readyState === WebSocket.CLOSED) {
    console.log('WebSocket connection closed, attempting reconnect...');
    reconnectWebSocket();
}
```

**API Authentication Errors:**
```bash
# Test API endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/experiments
```

### Performance Optimization

**Large Result Sets:**
- Enable pagination for result tables
- Use data streaming for live updates
- Implement client-side filtering
- Cache frequently accessed data

**WebSocket Performance:**
- Limit message frequency for high-volume logs
- Use message batching for multiple updates
- Implement selective subscriptions

---

## Best Practices

1. **Use Pagination**: Implement pagination for large result sets
2. **Cache Results**: Cache frequently accessed analysis data
3. **Secure APIs**: Always use authentication for production deployments
4. **Monitor Resources**: Track web application resource usage
5. **Backup Data**: Regular backups of experiment results and configurations
6. **Version Control**: Track configuration changes through the web interface
7. **User Management**: Implement proper user roles and permissions
8. **Error Handling**: Provide clear error messages and recovery options

The PANTHER web interface provides a comprehensive platform for managing protocol testing experiments, from initial design through result analysis, making complex testing workflows accessible to both technical and non-technical users.
