"""
AutoRun v2 - Configuration Management Module

Handles YAML configuration loading, saving, validation, and migration from v1 JSON format.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path
import json
from ruamel.yaml import YAML
from collections import defaultdict


# Custom exceptions
class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigLoadError(Exception):
    """Raised when configuration cannot be loaded"""
    pass


@dataclass
class AutoRunMetadata:
    """AutoRun system metadata and settings"""
    version: str = "1.0"
    dashboard_port: int = 80
    log_level: str = "INFO"
    default_user: str = "sodori"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ServiceConfig:
    """Configuration for a managed service"""
    name: str
    enabled: bool
    folder: str
    entrypoint: str
    port: Optional[int] = None
    web_interface: bool = False
    auto_restart: str = "always"
    description: str = ""
    environment: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)

    @property
    def service_filename(self) -> str:
        """Returns systemd service filename with autorun- prefix"""
        return f"autorun-{self.name}.service"

    @property
    def service_path(self) -> Path:
        """Returns full path to systemd service file"""
        return Path(f"/etc/systemd/system/{self.service_filename}")

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class AutoRunConfig:
    """Complete AutoRun configuration"""
    metadata: AutoRunMetadata
    services: List[ServiceConfig]

    def to_dict(self) -> dict:
        """Convert to dictionary structure for YAML"""
        return {
            "autorun": self.metadata.to_dict(),
            "services": [svc.to_dict() for svc in self.services]
        }


def load_config(config_path: Path = Path("autorun.yaml")) -> AutoRunConfig:
    """
    Load and parse YAML configuration

    Args:
        config_path: Path to YAML configuration file

    Returns:
        AutoRunConfig object

    Raises:
        ConfigLoadError: If file cannot be loaded or parsed
    """
    try:
        if not config_path.exists():
            raise ConfigLoadError(f"Configuration file not found: {config_path}")

        yaml = YAML()
        with open(config_path, 'r') as f:
            data = yaml.load(f)

        if not data:
            raise ConfigLoadError(f"Configuration file is empty: {config_path}")

        # Parse metadata
        metadata_data = data.get('autorun', {})
        metadata = AutoRunMetadata(**metadata_data)

        # Parse services
        services_data = data.get('services', [])
        services = []
        for svc_data in services_data:
            # Ensure required fields are present
            if 'name' not in svc_data:
                raise ConfigLoadError("Service missing required 'name' field")
            if 'folder' not in svc_data:
                raise ConfigLoadError(f"Service '{svc_data.get('name')}' missing required 'folder' field")
            if 'entrypoint' not in svc_data:
                raise ConfigLoadError(f"Service '{svc_data.get('name')}' missing required 'entrypoint' field")

            services.append(ServiceConfig(**svc_data))

        return AutoRunConfig(metadata=metadata, services=services)

    except Exception as e:
        if isinstance(e, (ConfigLoadError, ConfigValidationError)):
            raise
        raise ConfigLoadError(f"Failed to load configuration: {e}")


def save_config(config: AutoRunConfig, config_path: Path = Path("autorun.yaml")) -> None:
    """
    Save configuration to YAML file (preserves comments)

    Args:
        config: AutoRunConfig object to save
        config_path: Path to save configuration
    """
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=0)

    data = config.to_dict()

    with open(config_path, 'w') as f:
        yaml.dump(data, f)


def validate_config(config: AutoRunConfig, strict: bool = False) -> List[str]:
    """
    Validate configuration and return list of errors

    Args:
        config: AutoRunConfig object to validate
        strict: If False, folder/file existence checks are warnings only (default: False)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check for duplicate service names
    names = [svc.name for svc in config.services]
    name_counts = defaultdict(int)
    for name in names:
        name_counts[name] += 1

    for name, count in name_counts.items():
        if count > 1:
            errors.append(f"Duplicate service name: '{name}' appears {count} times")

    # Validate each service
    for svc in config.services:
        # Check folder exists (warning only in non-strict mode)
        folder_path = Path(svc.folder)
        if not folder_path.exists():
            if strict:
                errors.append(f"Service '{svc.name}': Folder does not exist: {svc.folder}")
            # In non-strict mode, just skip the warning - service can be configured before folder exists
        elif not folder_path.is_dir():
            errors.append(f"Service '{svc.name}': Path is not a directory: {svc.folder}")

        # Check entrypoint exists (warning only in non-strict mode)
        if folder_path.exists():
            entrypoint_path = folder_path / svc.entrypoint
            if not entrypoint_path.exists():
                if strict:
                    errors.append(f"Service '{svc.name}': Entrypoint file does not exist: {entrypoint_path}")
            elif not entrypoint_path.is_file():
                errors.append(f"Service '{svc.name}': Entrypoint is not a file: {entrypoint_path}")

        # Validate port
        if svc.port is not None:
            if not (1 <= svc.port <= 65535):
                errors.append(f"Service '{svc.name}': Invalid port number: {svc.port} (must be 1-65535)")

        # Validate restart policy
        valid_policies = ['always', 'on-failure', 'no']
        if svc.auto_restart not in valid_policies:
            errors.append(f"Service '{svc.name}': Invalid auto_restart policy: '{svc.auto_restart}' (must be one of: {', '.join(valid_policies)})")

        # Validate dependencies exist
        for dep in svc.depends_on:
            if dep not in names:
                errors.append(f"Service '{svc.name}': Dependency '{dep}' not found in service list")

    # Check for port conflicts
    port_users = defaultdict(list)
    for svc in config.services:
        if svc.port is not None:
            port_users[svc.port].append(svc.name)

    for port, users in port_users.items():
        if len(users) > 1:
            errors.append(f"Port conflict: Port {port} is used by multiple services: {', '.join(users)}")

    # Check for circular dependencies
    circular_deps = _find_circular_dependencies(config.services)
    if circular_deps:
        for cycle in circular_deps:
            errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")

    return errors


def _find_circular_dependencies(services: List[ServiceConfig]) -> List[List[str]]:
    """
    Find circular dependencies using DFS

    Returns:
        List of circular dependency chains
    """
    # Build adjacency list
    graph = {svc.name: svc.depends_on for svc in services}

    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(node: str, path: List[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        if node in graph:
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

        rec_stack.remove(node)

    for svc in services:
        if svc.name not in visited:
            dfs(svc.name, [])

    return cycles


def migrate_from_json(json_path: Path) -> AutoRunConfig:
    """
    Migrate configuration from v1 JSON format to v2 YAML format

    Args:
        json_path: Path to run.json file

    Returns:
        AutoRunConfig object
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        # Create default metadata
        metadata = AutoRunMetadata()

        # Migrate instances to services
        services = []
        instances = data.get('instances', [])

        for inst in instances:
            # Map v1 fields to v2 fields
            service = ServiceConfig(
                name=inst.get('id', '').replace('_', '-'),  # Use id as name
                enabled=inst.get('auto_start', True),       # auto_start -> enabled
                folder=inst.get('path', ''),
                entrypoint=inst.get('entry', 'run.py'),
                port=inst.get('port'),
                web_interface=inst.get('port') is not None,  # Has port = web interface
                auto_restart='always' if inst.get('auto_start', True) else 'no',
                description=inst.get('name', ''),            # Use name as description
                environment=inst.get('env', {}),
                depends_on=[]
            )
            services.append(service)

        config = AutoRunConfig(metadata=metadata, services=services)

        # Validate migrated config
        errors = validate_config(config)
        if errors:
            print("Warning: Migrated configuration has validation errors:")
            for error in errors:
                print(f"  - {error}")

        return config

    except Exception as e:
        raise ConfigLoadError(f"Failed to migrate from JSON: {e}")


def create_default_config() -> AutoRunConfig:
    """
    Create a default configuration with example service

    Returns:
        AutoRunConfig with default settings
    """
    metadata = AutoRunMetadata()

    services = [
        ServiceConfig(
            name="example-service",
            enabled=False,  # Disabled by default
            folder="/home/sodori/example",
            entrypoint="run.py",
            port=5001,
            web_interface=True,
            auto_restart="always",
            description="Example service (disabled)",
            environment={},
            depends_on=[]
        )
    ]

    return AutoRunConfig(metadata=metadata, services=services)
