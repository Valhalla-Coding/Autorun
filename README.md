# AutoRun v2 - Systemd Service Manager

AutoRun v2 is a Flask-based web dashboard for managing Python applications as systemd services. It provides a central control hub for your server, running on port 80 with a modern web interface for service management.

## Core Philosophy

**Configuration over Process Management**
- AutoRun manages systemd service CONFIGURATIONS, not processes directly
- systemd handles all process lifecycle (start, stop, restart, crashes)
- Declarative approach: describe what should run, let Linux make it happen

## Features

✅ **Systemd Integration** - Generates and manages systemd service files
✅ **Web Dashboard** - Modern, responsive UI for service management
✅ **YAML Configuration** - Clean, human-readable configuration
✅ **Service Control** - Start, stop, restart services with a click
✅ **Real-time Status** - Live service status monitoring
✅ **Auto-restart Policies** - Configure service restart behavior
✅ **Service Dependencies** - Manage service startup order
✅ **Environment Variables** - Configure per-service environment

## Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Preparing Your Python Applications](#preparing-your-python-applications)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Requirements

- **OS**: Linux with systemd (Ubuntu, Debian, CentOS, etc.)
- **Python**: Python 3.8 or higher
- **Permissions**: Sudo access for systemd management
- **Network**: Available port for dashboard (default: 5050)

## Quick Start

### Installation

1. Clone the repository:
```bash
cd ~
git clone https://github.com/your-username/autorun.git
cd autorun
```
Replace `your-username` with the actual GitHub repository owner.

2. Create your configuration file:
```bash
cp autorun.yaml.example autorun.yaml
```

3. Edit `autorun.yaml` and customize:
```bash
nano autorun.yaml
```

**Important settings to change**:
- `default_user`: Change to your Linux username (find with `whoami`)
- `dashboard_port`: Recommended 5050 (ports below 1024 require root)
- Remove or disable the example service

4. Run the installation script:
```bash
chmod +x install.sh
./install.sh
```

The installer will:
- Install Python dependencies
- Configure sudo permissions for systemctl
- Create AutoRun as a systemd service
- Start AutoRun automatically

5. Access the dashboard:
```
http://localhost:5050
```
(Replace 5050 with your configured dashboard_port)

### Manual Installation

If you prefer manual installation or development mode:

1. Create your configuration:
```bash
cp autorun.yaml.example autorun.yaml
nano autorun.yaml  # Edit with your settings
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Run AutoRun manually (development mode):
```bash
python3 autorun.py
```

**Note**: Manual mode won't have systemd service integration or sudo permissions configured. For production use, run the installation script.

## Configuration

### autorun.yaml

AutoRun uses a YAML configuration file to define services.

**First time setup**: Copy the example configuration and edit it:
```bash
cp autorun.yaml.example autorun.yaml
nano autorun.yaml
```

Example configuration:

```yaml
autorun:
  version: '1.0'
  dashboard_port: 5050  # Use port > 1024 to avoid permission issues
  log_level: INFO
  default_user: your-username  # Change to your Linux username

services:
  - name: my-flask-app
    enabled: true
    folder: /home/sodori/apps/my-flask-app
    entrypoint: run.py
    port: 5001
    web_interface: true
    auto_restart: always
    description: "My Flask Application"
    environment:
      DEBUG: "false"
      LOG_LEVEL: "INFO"
    depends_on: []
```

### Service Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique service identifier (lowercase, hyphens) |
| `enabled` | boolean | Yes | Whether to enable service on boot |
| `folder` | string | Yes | Full path to service directory |
| `entrypoint` | string | Yes | Python file to execute (default: run.py) |
| `port` | integer | No | Port number for web services |
| `web_interface` | boolean | No | Whether service has a web UI |
| `auto_restart` | string | No | Restart policy: always, on-failure, no |
| `description` | string | No | Human-readable description |
| `environment` | dict | No | Environment variables |
| `depends_on` | list | No | List of service dependencies |

## Usage

### Adding a Service

1. Click **"+ Add Service"** in the dashboard
2. Fill in the service details:
   - **Name**: Unique identifier (e.g., `my-service`)
   - **Folder**: Full path to your application (e.g., `/home/user/myapp`)
   - **Entrypoint**: Python file to run (usually `run.py`)
   - **Port**: Optional port number if it's a web service
   - **Auto Restart**: Choose restart policy
   - **Description**: Brief description
3. Click **"Save Service"**

AutoRun will:
- Add the service to `autorun.yaml`
- Generate a systemd service file in `/etc/systemd/system/`
- Run `systemctl daemon-reload`
- Enable the service if checked

### Managing Services

**Start a Service**: Click the ▶️ button
**Stop a Service**: Click the ⏹️ button
**Restart a Service**: Click the 🔄 button
**Edit a Service**: Click the ✏️ button
**Delete a Service**: Click the 🗑️ button

### System Controls

**Reload Config**: Reload `autorun.yaml` and regenerate all systemd files
**Daemon Reload**: Run `systemctl daemon-reload`
**Apply All Changes**: Equivalent to Reload Config

## Preparing Your Python Applications

Before adding your Python applications to AutoRun, ensure they meet these requirements:

### Prerequisites

1. **Application Structure**: Your app should have a main Python file (e.g., `run.py`, `app.py`, `main.py`)
2. **Dependencies**: A `requirements.txt` file in your application folder
3. **Long-Running Process**: The entrypoint must keep running (see examples below)

### Service Requirements

Your Python applications must meet these requirements:

### 1. Long-Running Process

The entrypoint file must keep the process running:

```python
# run.py - GOOD ✓
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "Hello!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  # Stays running
```

**Avoid** scripts that exit immediately:
```python
# run.py - BAD ✗
import subprocess
subprocess.Popen(['python3', 'main.py'])  # Exits immediately
```

### 2. Environment Variables

Services can access environment variables:
```python
import os

PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
```

### 3. Working Directory

The service runs with its folder as the working directory:
```python
# Files are relative to service folder
with open('config.json') as f:  # Loads ./config.json
    config = json.load(f)
```

## Architecture

### Technology Stack

- **Backend**: Python 3 + Flask
- **Frontend**: HTML/CSS/JavaScript
- **Config**: YAML (ruamel.yaml)
- **Process Management**: systemd
- **Logging**: journalctl integration

### Project Structure

```
autorun/
├── autorun.py              # Main Flask application
├── config.py               # YAML config management
├── systemd_manager.py      # Systemd integration
├── autorun.yaml            # Service configuration
├── requirements.txt        # Python dependencies
├── install.sh              # Installation script
├── templates/
│   ├── base.html           # Dashboard layout
│   └── management.html     # Management tab
└── static/
    ├── css/
    │   └── style.css       # Dashboard styling
    └── js/
        ├── utils.js        # API wrapper
        ├── tabs.js         # Tab management
        └── services.js     # Service management
```

### How It Works

1. **Configuration**: User defines services in `autorun.yaml`
2. **Service Generation**: AutoRun generates systemd `.service` files
3. **Systemd Management**: systemd manages the actual processes
4. **Status Monitoring**: Dashboard queries systemctl for live status
5. **Control**: Web UI sends commands via systemctl

## API Endpoints

AutoRun provides a REST API for programmatic access:

### Service Management
- `GET /api/services` - List all services
- `GET /api/services/<name>` - Get service details
- `POST /api/services` - Create service
- `PUT /api/services/<name>` - Update service
- `DELETE /api/services/<name>` - Delete service

### Service Control
- `POST /api/services/<name>/start` - Start service
- `POST /api/services/<name>/stop` - Stop service
- `POST /api/services/<name>/restart` - Restart service
- `POST /api/services/<name>/enable` - Enable service
- `POST /api/services/<name>/disable` - Disable service

### System
- `POST /api/system/reload` - Reload configuration
- `POST /api/system/daemon-reload` - Run daemon-reload
- `GET /api/system/status` - System status
- `GET /api/health` - Health check

## Troubleshooting

### AutoRun won't start

Check logs:
```bash
sudo journalctl -u autorun -xe
```

Common issues:
- **Port already in use**: Change `dashboard_port` in `autorun.yaml`
- **Missing dependencies**: Run `pip3 install -r requirements.txt`
- **Permission errors**: Check sudoers configuration

### "Permission denied" error on startup

If you see "Permission denied" when AutoRun tries to start:

**Cause**: Ports below 1024 (like port 80) require root privileges to bind.

**Solution**: Edit `autorun.yaml` and change `dashboard_port` to a port above 1024:
```yaml
autorun:
  dashboard_port: 5050  # Use 5050, 8080, 8000, or any port > 1024
```

Then restart:
```bash
sudo systemctl restart autorun
```

Access the dashboard at `http://localhost:5050` (replace with your chosen port).

### Browser shows SSL/HTTPS errors

If you see `SSL_ERROR_RX_RECORD_TOO_LONG` or similar:

**Cause**: Your browser is trying to use HTTPS, but AutoRun serves plain HTTP.

**Solutions**:
1. Make sure you're using `http://` (not `https://`) in the URL
2. Clear browser HSTS cache:
   - Chrome/Edge: Go to `chrome://net-internals/#hsts` or `edge://net-internals/#hsts`
   - Delete domain for `127.0.0.1` or `localhost`
3. Try a different browser or incognito/private mode

### Service won't start

Check service logs:
```bash
sudo journalctl -u <service-name> -xe
```

Common issues:
- Python file path wrong: Verify `folder` and `entrypoint`
- Missing Python dependencies: Install in service folder
- Port already in use: Change port in service configuration

### Permission denied errors

Verify sudoers configuration:
```bash
sudo cat /etc/sudoers.d/autorun
```

Should allow systemctl commands without password.

## Systemd Commands

Useful commands for managing AutoRun:

```bash
# View status
sudo systemctl status autorun

# View logs (live)
sudo journalctl -u autorun -f

# Restart AutoRun
sudo systemctl restart autorun

# Stop AutoRun
sudo systemctl stop autorun

# Disable AutoRun
sudo systemctl disable autorun
```

## Development

### Running in Development Mode

```bash
python3 autorun.py
```

Dashboard will be available at `http://localhost:80` (or configured port).

### Testing Configuration

Test YAML configuration:
```bash
python3 -c "import config; c = config.load_config(); print(c.services)"
```

### Generating Service Files (Dry Run)

```python
import config
import systemd_manager

cfg = config.load_config()
for svc in cfg.services:
    content = systemd_manager.generate_service_file(svc, 'sodori')
    print(content)
```

## Roadmap

### Phase 1 (Current)
- ✅ YAML configuration
- ✅ Systemd service generation
- ✅ Web dashboard (Management tab)
- ✅ Service CRUD operations
- ✅ Service control (start/stop/restart)

### Phase 2 (Future)
- [ ] Console tab with log viewer
- [ ] Real-time log streaming (WebSocket)
- [ ] Dynamic service tabs with iframes
- [ ] Reverse proxy implementation
- [ ] Service health checks

### Phase 3 (Future)
- [ ] User authentication
- [ ] Resource usage graphs (CPU, RAM)
- [ ] Email/Slack alerts
- [ ] Mobile-responsive design
- [ ] API key authentication

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/autorun/issues
- Documentation: https://github.com/yourusername/autorun/wiki

## Credits

Developed by [Your Name]

Built with Flask, systemd, and modern web technologies.
