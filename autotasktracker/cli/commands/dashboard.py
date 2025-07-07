"""Dashboard-related CLI commands."""
import click
import logging
import subprocess
import time
import os
from pathlib import Path
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


@click.group(name='dashboard')
def dashboard_group():
    """Dashboard management commands."""
    pass


@dashboard_group.command()
@click.option('--type', '-t', 
              type=click.Choice(['task', 'analytics', 'time', 'all']), 
              default='task',
              help='Dashboard type to start')
@click.option('--port', '-p', type=int, help='Custom port number')
@click.option('--browser/--no-browser', default=True, help='Open browser automatically')
def start(type, port, browser):
    """Start dashboard(s)."""
    from autotasktracker import dashboard as task_dashboard
    from autotasktracker import analytics, timetracker
    
    config = get_config()
    
    dashboards = {
        'task': {
            'name': 'Task Board',
            'module': 'autotasktracker.dashboards.task_board',
            'default_port': config.TASK_BOARD_PORT,
            'icon': '📋'
        },
        'analytics': {
            'name': 'Analytics',
            'module': 'autotasktracker.dashboards.analytics', 
            'default_port': config.ANALYTICS_PORT,
            'icon': '📊'
        },
        'time': {
            'name': 'Time Tracker',
            'module': 'autotasktracker.dashboards.timetracker',
            'default_port': config.TIMETRACKER_PORT,
            'icon': '⏱️'
        }
    }
    
    if type == 'all':
        click.echo("🚀 Starting all dashboards...")
        for dash_type, config in dashboards.items():
            _start_dashboard(config, browser=browser and dash_type == 'task')
            time.sleep(2)  # Give each dashboard time to start
    else:
        config = dashboards[type]
        if port:
            config['default_port'] = port
        _start_dashboard(config, browser=browser)


def _start_dashboard(config, browser=True):
    """Start a single dashboard."""
    click.echo(f"{config['icon']} Starting {config['name']} on port {config['default_port']}...")
    
    cmd = [
        'streamlit', 'run',
        f"{config['module'].replace('.', '/')}.py",
        '--server.port', str(config['default_port']),
        '--server.headless', 'true'
    ]
    
    if not browser:
        cmd.extend(['--server.browser.open', 'false'])
    
    try:
        # Start in background
        process = subprocess.Popen(cmd)
        click.echo(f"✅ {config['name']} started (PID: {process.pid})")
        
        # Save PID for later
        pid_file = Path(f".{config['name'].lower().replace(' ', '_')}.pid")
        pid_file.write_text(str(process.pid))
        
        if browser:
            click.echo(f"   Opening http://localhost:{config['default_port']}")
    except Exception as e:
        click.echo(f"❌ Failed to start {config['name']}: {e}")


@dashboard_group.command()
@click.option('--type', '-t',
              type=click.Choice(['task', 'analytics', 'time', 'all']),
              default='all',
              help='Dashboard type to stop')
def stop(type):
    """Stop dashboard(s)."""
    dashboards = {
        'task': 'task_board',
        'analytics': 'analytics',
        'time': 'time_tracker'
    }
    
    if type == 'all':
        for dash_type in dashboards:
            _stop_dashboard(dashboards[dash_type])
    else:
        _stop_dashboard(dashboards[type])


def _stop_dashboard(name):
    """Stop a single dashboard."""
    pid_file = Path(f".{name}.pid")
    
    if not pid_file.exists():
        click.echo(f"❌ {name} is not running (no PID file)")
        return
    
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 15)  # SIGTERM
        pid_file.unlink()
        click.echo(f"✅ Stopped {name} (PID: {pid})")
    except ProcessLookupError:
        pid_file.unlink()
        click.echo(f"❌ {name} process not found (cleaned up PID file)")
    except Exception as e:
        click.echo(f"❌ Failed to stop {name}: {e}")


@dashboard_group.command()
def status():
    """Check dashboard status."""
    import requests
    
    config = get_config()
    
    dashboards = [
        {'name': 'Task Board', 'port': config.TASK_BOARD_PORT},
        {'name': 'Analytics', 'port': config.ANALYTICS_PORT},
        {'name': 'Time Tracker', 'port': config.TIMETRACKER_PORT}
    ]
    
    click.echo("📊 Dashboard Status")
    click.echo("=" * 40)
    
    for dashboard in dashboards:
        try:
            response = requests.get(f"http://localhost:{dashboard['port']}", timeout=2)
            if response.status_code == 200:
                click.echo(f"✅ {dashboard['name']:<15} Running on port {dashboard['port']}")
            else:
                click.echo(f"⚠️  {dashboard['name']:<15} Responding but not healthy")
        except requests.exceptions.RequestException:
            click.echo(f"❌ {dashboard['name']:<15} Not running")


@dashboard_group.command()
def launcher():
    """Launch interactive dashboard selector."""
    from scripts.dashboard_launcher import main as launcher_main
    
    click.echo("🚀 Starting interactive dashboard launcher...")
    launcher_main()