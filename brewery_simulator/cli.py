"""
brewery_simulator/cli.py

Usage:
  uv run brewery-sim                       # real-time + API on :8000
  uv run brewery-sim --speed 3600          # turbo
  uv run brewery-sim --no-api              # disable HTTP API
  uv run brewery-sim --api-port 9000       # custom API port
  uv run brewery-sim --dry-run             # validate config and exit
  uv run brewery-sim tags                  # list all tags
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="brewery-sim",
    help="🍺  Industrial Brewery PLC Simulator — publishes all IOs via MQTT5",
    rich_markup_mode="rich",
    invoke_without_command=True,
    no_args_is_help=False,
)

console = Console()

SPEED_PRESETS = {
    "realtime": 1.0,
    "fast":     60.0,
    "turbo":    3600.0,
    "warp":     86400.0,
}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
    logging.getLogger("aiomqtt").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)


def _find_config(path: Optional[Path], filename: str) -> Path:
    if path and path.exists():
        return path
    for candidate in [Path.cwd() / filename, Path(__file__).parent.parent / filename]:
        if candidate.exists():
            return candidate
    console.print(f"[red]Config file '{filename}' not found.[/red]")
    raise typer.Exit(1)


def _print_banner(engine) -> None:
    speed = engine.speed
    if speed >= 3600:
        speed_label = f"[cyan]{speed:.0f}x[/cyan]  ({speed/3600:.1f} sim-hours / real-second)"
    else:
        speed_label = f"[cyan]{speed:.0f}x[/cyan]  ({speed:.0f} sim-seconds / real-second)"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[bold]Speed[/bold]",       speed_label)
    table.add_row("[bold]MQTT Broker[/bold]",  f"[green]{engine.cfg.mqtt.host}:{engine.cfg.mqtt.port}[/green]")
    table.add_row("[bold]Tags[/bold]",         str(len(engine.store.all_tags())))
    if engine.api_enabled:
        table.add_row("[bold]Control API[/bold]", f"[green]http://{engine.api_host}:{engine.api_port}/docs[/green]")
    else:
        table.add_row("[bold]Control API[/bold]", "[dim]disabled[/dim]")
    console.print(Panel(table, title="🍺  Brewery Simulator", border_style="blue"))


# ── Main command ──────────────────────────────────────────────────────────────

@app.callback()
def main(
    ctx:      typer.Context,
    speed:    Optional[float] = typer.Option(None,  "--speed",    "-s", help="Speed multiplier (1=realtime, 3600=turbo)"),
    preset:   Optional[str]   = typer.Option(None,  "--preset",   "-p", help="realtime | fast | turbo | warp"),
    host:     Optional[str]   = typer.Option(None,  "--host",           help="MQTT broker hostname"),
    port:     Optional[int]   = typer.Option(None,  "--port",           help="MQTT broker port"),
    config:   Optional[Path]  = typer.Option(None,  "--config",   "-c", help="Path to config.toml"),
    tags_file:Optional[Path]  = typer.Option(None,  "--tags",     "-t", help="Path to tags.toml"),
    api_port: int             = typer.Option(8000,  "--api-port",       help="HTTP control API port"),
    api_host: str             = typer.Option("0.0.0.0", "--api-host",   help="HTTP control API bind address"),
    no_api:   bool            = typer.Option(False, "--no-api",         help="Disable the HTTP control API"),
    verbose:  bool            = typer.Option(False, "--verbose",  "-v", help="Debug logging"),
    dry_run:  bool            = typer.Option(False, "--dry-run",        help="Validate config and exit"),
) -> None:
    """Start the brewery simulator with live HTTP control API."""
    if ctx.invoked_subcommand is not None:
        return

    _setup_logging(verbose)

    # Resolve speed
    if preset:
        if preset not in SPEED_PRESETS:
            console.print(f"[red]Unknown preset '{preset}'. Options: {list(SPEED_PRESETS)}[/red]")
            raise typer.Exit(1)
        speed_val = SPEED_PRESETS[preset]
    else:
        speed_val = speed

    config_path = _find_config(config,    "config.toml")
    tags_path   = _find_config(tags_file, "tags.toml")

    from brewery_simulator.engine import BreweryEngine
    engine = BreweryEngine(
        config_path, tags_path,
        speed=speed_val,
        api_host=api_host,
        api_port=api_port,
        api_enabled=not no_api,
    )

    if host: engine.cfg.mqtt.host = host
    if port: engine.cfg.mqtt.port = port

    _print_banner(engine)

    if dry_run:
        by_type: dict[str, int] = {}
        for ts in engine.store.all_tags().values():
            by_type[ts.meta.io_type] = by_type.get(ts.meta.io_type, 0) + 1
        console.print(f"\n[bold green]✓ Dry run OK.[/bold green] {len(engine.store.all_tags())} tags:")
        for t, n in sorted(by_type.items()):
            console.print(f"  {t}: {n}")
        raise typer.Exit(0)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Simulator stopped.[/yellow]")


# ── Subcommand: list tags ─────────────────────────────────────────────────────

@app.command("tags")
def list_tags(
    tags_file: Optional[Path] = typer.Option(None, "--tags", "-t"),
    area:      Optional[str]  = typer.Option(None, "--area", "-a"),
    io_type:   Optional[str]  = typer.Option(None, "--type"),
) -> None:
    """List all configured tags."""
    _setup_logging(False)
    tags_path = _find_config(tags_file, "tags.toml")
    from brewery_simulator.tag_store import TagStore
    store = TagStore()
    store.load_from_toml(tags_path)

    table = Table(title="Tag Registry", show_lines=False)
    table.add_column("Tag",         style="cyan",    no_wrap=True)
    table.add_column("Type",        style="green",   width=4)
    table.add_column("Area",        style="yellow")
    table.add_column("Equip",       style="magenta")
    table.add_column("Unit",        style="white")
    table.add_column("Description")

    count = 0
    for name, state in sorted(store.all_tags().items()):
        if area    and state.meta.area     != area:          continue
        if io_type and state.meta.io_type  != io_type.upper(): continue
        table.add_row(name, state.meta.io_type, state.meta.area,
                      state.meta.equipment, state.meta.unit, state.meta.description)
        count += 1

    console.print(table)
    console.print(f"\nTotal: [bold]{count}[/bold] tags")


if __name__ == "__main__":
    app()
