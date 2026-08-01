"""Command-line interface for Aether Home Concierge."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from aether import __version__

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """Aether - Home Concierge.

    Your home, managed. Your mind, free.
    """
    pass


@main.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the Aether web server."""
    import uvicorn
    console.print(f"[bold green]Starting Aether on http://{host}:{port}[/bold green]")
    uvicorn.run(
        "aether.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@main.command()
@click.option("--reset", is_flag=True, help="Reset database before seeding (WARNING: deletes all data)")
def seed(reset: bool):
    """Seed the database with initial data."""
    from aether.seed.seeder import seed_database
    seed_database(reset=reset)


@main.command()
def dashboard():
    """Show the home dashboard."""
    from aether.core import Prioritizer

    dash = Prioritizer.get_dashboard()

    # Overall status
    console.print()
    status_color = "green" if dash.overall_freshness >= 70 else "yellow" if dash.overall_freshness >= 40 else "red"
    console.print(Panel(
        f"[bold {status_color}]{dash.overall_freshness}% Fresh[/bold {status_color}]\n"
        f"[dim]{dash.total_overdue} overdue · {dash.chores_due_soon} due soon[/dim]",
        title="[bold]Home Status[/bold]",
    ))

    # Rooms table
    table = Table(title="Rooms")
    table.add_column("Room", style="bold")
    table.add_column("Freshness", justify="center")
    table.add_column("Overdue", justify="center")

    for room in dash.rooms:
        color = "green" if room.freshness_percent >= 70 else "yellow" if room.freshness_percent >= 40 else "red"
        overdue = f"[red]{room.overdue_count}[/red]" if room.overdue_count > 0 else "[dim]0[/dim]"
        table.add_row(
            f"{room.icon} {room.name}",
            f"[{color}]{room.freshness_percent}%[/{color}]",
            overdue,
        )

    console.print(table)

    # House-wide chores
    if dash.house_wide_chores:
        console.print("\n[bold]House-wide Chores[/bold]")
        for chore in dash.house_wide_chores[:5]:
            status = "[red]overdue[/red]" if chore.is_overdue else f"due in {chore.days_until_due}d"
            console.print(f"  · {chore.name} ({status})")


@main.command()
def briefing():
    """Show the morning briefing."""
    from aether.core import Prioritizer

    brief = Prioritizer.get_morning_briefing()

    console.print()
    console.print(Panel(
        f"[bold]{brief.greeting}![/bold]\n\n"
        f"Here's about [cyan]{brief.total_minutes} minutes[/cyan] of high-impact tasks:",
        title="[bold]Daily Briefing[/bold]",
    ))

    if brief.suggested_chores:
        for chore in brief.suggested_chores:
            room = f"[dim]({chore.room_name})[/dim]" if chore.room_name else "[dim](house-wide)[/dim]"
            console.print(f"  · {chore.name} {room} [dim]~{chore.estimated_minutes}min[/dim]")
    else:
        console.print("  [green]All caught up![/green]")


@main.command("quick")
@click.argument("minutes", type=int)
def quick_clean(minutes: int):
    """Get prioritized chores for available time.

    Example: aether quick 30
    """
    from aether.core import Prioritizer

    result = Prioritizer.get_quick_clean(minutes)

    console.print()
    console.print(Panel(
        f"[bold]You have {minutes} minutes[/bold]\n\n"
        f"{result.impact_summary}",
        title="[bold]Quick Clean[/bold]",
    ))

    if result.chores:
        table = Table()
        table.add_column("Chore", style="bold")
        table.add_column("Room")
        table.add_column("Time", justify="right")

        for chore in result.chores:
            room = chore.room_name or "House-wide"
            table.add_row(chore.name, room, f"{chore.estimated_minutes}min")

        console.print(table)
        console.print(f"\n[dim]Total: {result.total_minutes} minutes[/dim]")
    else:
        console.print("[green]All caught up![/green]")


@main.command()
@click.argument("chore_id")
def done(chore_id: str):
    """Mark a chore as complete.

    Example: aether done abc123
    """
    from aether.core import ChoreService

    chore = ChoreService.complete(chore_id)
    if not chore:
        console.print(f"[red]Chore not found: {chore_id}[/red]")
        return

    if chore.streak > 1:
        console.print(f"[green]Done![/green] {chore.name} - [cyan]{chore.streak} in a row[/cyan]")
    else:
        console.print(f"[green]Done![/green] {chore.name}")


@main.command()
def rooms():
    """List all rooms."""
    from aether.core import RoomService

    rooms_list = RoomService.get_all_with_freshness()

    table = Table(title="Rooms")
    table.add_column("ID", style="dim")
    table.add_column("Room")
    table.add_column("Chores", justify="center")
    table.add_column("Freshness", justify="center")

    for room in rooms_list:
        color = "green" if room.freshness_percent >= 70 else "yellow" if room.freshness_percent >= 40 else "red"
        table.add_row(
            room.id,
            f"{room.icon} {room.name}",
            str(room.chore_count),
            f"[{color}]{room.freshness_percent}%[/{color}]",
        )

    console.print(table)


@main.command()
def overdue():
    """List all overdue chores."""
    from aether.core import ChoreService

    chores = ChoreService.get_overdue()

    if not chores:
        console.print("[green]No overdue chores![/green]")
        return

    table = Table(title=f"Overdue Chores ({len(chores)})")
    table.add_column("ID", style="dim")
    table.add_column("Chore")
    table.add_column("Room")
    table.add_column("Days Overdue", justify="right", style="red")

    for chore in chores:
        room = chore.room_name or "House-wide"
        days = abs(chore.days_until_due)
        table.add_row(chore.id, chore.name, room, str(days))

    console.print(table)


@main.command()
def checklists():
    """List all checklists."""
    from aether.core import ChecklistService

    lists = ChecklistService.get_all()

    if not lists:
        console.print("[dim]No checklists yet.[/dim]")
        return

    table = Table(title="Checklists")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Description")

    for cl in lists:
        table.add_row(cl.id, f"{cl.icon} {cl.name}", cl.description)

    console.print(table)


@main.command()
@click.argument("checklist_id")
def checklist(checklist_id: str):
    """Show a checklist with live chore status."""
    from aether.core import ChecklistService

    cl = ChecklistService.get_with_chores(checklist_id)
    if not cl:
        console.print(f"[red]Checklist not found: {checklist_id}[/red]")
        return

    console.print()
    console.print(Panel(
        f"[bold]{cl.icon} {cl.name}[/bold]\n"
        f"[dim]{cl.description}[/dim]\n\n"
        f"{len(cl.chores)} chores · ~{cl.total_minutes} min · {cl.overdue_count} overdue",
        title="Checklist",
    ))

    table = Table()
    table.add_column("Status", justify="center")
    table.add_column("Chore")
    table.add_column("Room")
    table.add_column("Due", justify="right")

    for chore in cl.chores:
        if chore.is_overdue:
            status = "[red]![/red]"
            due = f"[red]{abs(chore.days_until_due)}d overdue[/red]"
        elif chore.days_until_due <= 0:
            status = "[yellow]·[/yellow]"
            due = "[yellow]due[/yellow]"
        else:
            status = "[green]✓[/green]"
            due = f"[dim]{chore.days_until_due}d[/dim]"

        room = chore.room_name or "House-wide"
        table.add_row(status, chore.name, room, due)

    console.print(table)


@main.group()
def vacation():
    """Manage vacation mode."""
    pass


@vacation.command("start")
def vacation_start():
    """Start vacation mode, pausing eligible chores' countdowns."""
    from aether.core import VacationService

    try:
        VacationService.start()
        console.print("[green]Vacation mode started.[/green] Eligible chores are now paused.")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@vacation.command("end")
def vacation_end():
    """End vacation mode, shifting eligible chores' due dates forward."""
    from aether.core import VacationService

    try:
        result = VacationService.end()
        days = round(result.days_elapsed, 1)
        console.print(
            f"[green]Welcome back![/green] {result.chores_affected} chore(s) shifted forward by ~{days} day(s)."
        )
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@vacation.command("status")
def vacation_status():
    """Show current vacation mode status."""
    from aether.core import VacationService

    status = VacationService.get_status()
    if status.is_active:
        days = round(status.days_elapsed, 1)
        console.print(f"[green]Vacation mode is active[/green] — {days} day(s) so far.")
    else:
        console.print("[dim]Vacation mode is not active.[/dim]")


if __name__ == "__main__":
    main()
