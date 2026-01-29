"""Command-line interface for Aether."""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
import humanize

from .core.engine import Aether
from .data.models import TaskStatus, TaskPriority, EnergyLevel


console = Console()
aether = Aether()


# Helpers for rich output
def format_task_row(task, show_id=True):
    """Format a task for table display."""
    status_icons = {
        TaskStatus.INBOX: "📥",
        TaskStatus.TODO: "⬜",
        TaskStatus.IN_PROGRESS: "🔄",
        TaskStatus.WAITING: "⏸️",
        TaskStatus.DONE: "✅",
        TaskStatus.CANCELLED: "❌",
    }

    priority_colors = {
        TaskPriority.CRITICAL: "red bold",
        TaskPriority.HIGH: "red",
        TaskPriority.MEDIUM: "yellow",
        TaskPriority.LOW: "dim",
        TaskPriority.SOMEDAY: "dim italic",
    }

    icon = status_icons.get(task.status, "•")
    title = task.title
    if task.is_overdue:
        title = f"[red]{title}[/red]"
    elif task.priority.value <= 2:
        title = f"[{priority_colors[task.priority]}]{title}[/{priority_colors[task.priority]}]"

    due = ""
    if task.due_date:
        if task.is_overdue:
            due = f"[red]OVERDUE ({humanize.naturalday(task.due_date)})[/red]"
        else:
            due = humanize.naturalday(task.due_date)

    row = [icon, title]
    if show_id:
        row.insert(0, f"[dim]{task.id}[/dim]")

    row.extend([
        task.area or "",
        due,
    ])

    return row


def print_tasks_table(tasks, title="Tasks", show_id=True):
    """Print tasks in a table."""
    if not tasks:
        console.print(f"[dim]No {title.lower()} found.[/dim]")
        return

    table = Table(title=title, box=box.ROUNDED, show_header=True)

    if show_id:
        table.add_column("ID", style="dim", width=8)
    table.add_column("", width=2)
    table.add_column("Task", min_width=30)
    table.add_column("Area", width=12)
    table.add_column("Due", width=15)

    for task in tasks:
        table.add_row(*format_task_row(task, show_id))

    console.print(table)


def print_recommendations(recommendations, title="Recommended"):
    """Print recommended tasks with scores."""
    if not recommendations:
        console.print("[dim]No recommendations available.[/dim]")
        return

    table = Table(title=title, box=box.ROUNDED)
    table.add_column("ID", style="dim", width=8)
    table.add_column("Task", min_width=30)
    table.add_column("Score", width=8, justify="right")
    table.add_column("Reason", width=30)

    for task, score, reasoning in recommendations:
        reason = []
        if reasoning.get("urgency", 0) > 0.7:
            reason.append("urgent")
        if reasoning.get("energy_match", 0) > 0.7:
            reason.append("energy match")
        if reasoning.get("quick_win", 0) > 0.5:
            reason.append("quick win")
        if reasoning.get("momentum", 0) > 0.3:
            reason.append("momentum")

        table.add_row(
            task.id,
            task.title,
            f"{score:.1f}",
            ", ".join(reason) or "good fit",
        )

    console.print(table)


# Main CLI group
@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Aether - Your adaptive personal assistant.

    Run without a command to see quick status.
    """
    if ctx.invoked_subcommand is None:
        # Show quick status
        status = aether.status()

        console.print()
        console.print(Panel(
            f"[bold]Energy:[/bold] {status['energy']} | "
            f"[bold]Done today:[/bold] {status['tasks_today']} | "
            f"[bold]Overdue:[/bold] {status['overdue_count']}",
            title="Aether Status",
            box=box.ROUNDED,
        ))

        if status["in_progress"]:
            console.print("\n[bold]In Progress:[/bold]")
            for t in status["in_progress"]:
                console.print(f"  🔄 {t['title']} [{t['id']}]")

        if status["due_reminders"]:
            console.print("\n[bold]Due Reminders:[/bold]")
            for r in status["due_reminders"]:
                console.print(f"  🔔 {r['title']}")

        console.print()


# Task commands
@main.command()
@click.argument("text", nargs=-1, required=True)
def add(text):
    """Add a task quickly.

    Examples:
        aether add Buy milk #shopping @errands
        aether add Call mom !high due:tomorrow
        aether add Review PR est:30m @work +project-x
    """
    task_text = " ".join(text)
    task = aether.add(task_text)
    console.print(f"[green]✓[/green] Added: {task.title} [{task.id}]")
    if task.due_date:
        console.print(f"  Due: {humanize.naturalday(task.due_date)}")
    if task.area:
        console.print(f"  Area: {task.area}")


@main.command()
@click.argument("task_id")
@click.option("--time", "-t", type=int, help="Actual minutes spent")
def done(task_id, time):
    """Mark a task as complete."""
    task = aether.done(task_id, time)
    if task:
        console.print(f"[green]✓[/green] Completed: {task.title}")
    else:
        console.print(f"[red]✗[/red] Task not found: {task_id}")


@main.command()
@click.argument("task_id")
def start(task_id):
    """Start working on a task."""
    task = aether.start(task_id)
    if task:
        console.print(f"[blue]▶[/blue] Started: {task.title}")
    else:
        console.print(f"[red]✗[/red] Task not found: {task_id}")


@main.command()
@click.argument("task_id")
@click.option("--reason", "-r", default="", help="Reason for blocking")
def block(task_id, reason):
    """Mark a task as blocked."""
    task = aether.block(task_id, reason)
    if task:
        console.print(f"[yellow]⏸[/yellow] Blocked: {task.title}")
    else:
        console.print(f"[red]✗[/red] Task not found: {task_id}")


@main.command()
@click.argument("task_id")
def unblock(task_id):
    """Unblock a task."""
    task = aether.unblock(task_id)
    if task:
        console.print(f"[green]▶[/green] Unblocked: {task.title}")
    else:
        console.print(f"[red]✗[/red] Task not found: {task_id}")


@main.command(name="list")
@click.option("--area", "-a", help="Filter by area")
@click.option("--project", "-p", help="Filter by project")
@click.option("--all", "show_all", is_flag=True, help="Include completed tasks")
def list_tasks(area, project, show_all):
    """List tasks."""
    tasks = aether.tasks.list(area=area, project=project, include_done=show_all)
    print_tasks_table(tasks, "Tasks")


@main.command()
def inbox():
    """Show inbox items."""
    tasks = aether.inbox()
    print_tasks_table(tasks, "Inbox")
    if tasks:
        console.print("\n[dim]Use 'aether promote <id>' to move to TODO[/dim]")


@main.command()
@click.argument("task_id")
def promote(task_id):
    """Promote task from inbox to TODO."""
    task = aether.promote(task_id)
    if task:
        console.print(f"[green]✓[/green] Promoted: {task.title}")
    else:
        console.print(f"[red]✗[/red] Task not found: {task_id}")


@main.command()
def overdue():
    """Show overdue tasks."""
    tasks = aether.overdue()
    print_tasks_table(tasks, "Overdue Tasks")


@main.command()
def today():
    """Show tasks due today."""
    tasks = aether.today()
    print_tasks_table(tasks, "Due Today")


@main.command(name="next")
@click.option("--count", "-n", default=5, help="Number of tasks")
def next_tasks(count):
    """Get recommended next tasks based on context."""
    recommendations = aether.next(count)
    print_recommendations(recommendations, "Recommended Next")


@main.command()
@click.option("--count", "-n", default=5, help="Number of tasks")
def quick(count):
    """Get quick win tasks."""
    tasks = aether.quick_wins(count)
    print_tasks_table(tasks, "Quick Wins")


@main.command()
def blocked():
    """Show blocked tasks."""
    tasks = aether.blocked()
    print_tasks_table(tasks, "Blocked Tasks")


# Briefings
@main.command()
def morning():
    """Get morning briefing."""
    briefing = aether.morning()

    console.print()
    console.print(Panel(
        briefing["greeting"],
        title="Good Morning",
        box=box.DOUBLE,
    ))

    # Summary
    s = briefing["summary"]
    console.print(f"\n[bold]Summary:[/bold] {s['total_active']} active tasks | "
                  f"{s['overdue']} overdue | {s['due_today']} due today | "
                  f"{s['inbox']} in inbox")

    # Warnings
    if briefing["warnings"]:
        console.print("\n[bold red]Warnings:[/bold red]")
        for w in briefing["warnings"]:
            console.print(f"  ⚠️  {w['message']}")

    # Priorities
    if briefing["priorities"]:
        console.print("\n[bold]Top Priorities:[/bold]")
        for i, p in enumerate(briefing["priorities"], 1):
            due_str = f" (due {p['due']})" if p["due"] else ""
            console.print(f"  {i}. {p['title']}{due_str}")
            console.print(f"     [dim]{p['reason']}[/dim]")

    # Reminders
    if briefing["reminders"]:
        console.print("\n[bold]Upcoming Reminders:[/bold]")
        for r in briefing["reminders"]:
            time_str = r["time"] or "flexible"
            console.print(f"  🔔 {time_str} - {r['title']}")

    # Events
    if briefing["events"]:
        console.print("\n[bold]Today's Events:[/bold]")
        for e in briefing["events"]:
            prep = " [prep needed]" if e["prep_needed"] else ""
            console.print(f"  📅 {e['start']} - {e['title']} ({e['duration']}min){prep}")

    # Suggestions
    if briefing["suggestions"]:
        console.print("\n[bold]Suggestions:[/bold]")
        for sug in briefing["suggestions"]:
            console.print(f"  💡 {sug['message']}")

    console.print()


@main.command()
def weekly():
    """Get weekly review."""
    briefing = aether.weekly()

    console.print()
    console.print(Panel(
        f"Week of {briefing['period']['start']} to {briefing['period']['end']}",
        title="Weekly Review",
        box=box.DOUBLE,
    ))

    # Accomplishments
    acc = briefing["accomplishments"]
    console.print(f"\n[bold]Completed:[/bold] {acc['count']} tasks")

    if acc["by_area"]:
        console.print("  By area:", end=" ")
        console.print(", ".join(f"{k}: {v}" for k, v in acc["by_area"].items()))

    if acc["highlights"]:
        console.print("\n[bold]Highlights:[/bold]")
        for h in acc["highlights"]:
            console.print(f"  ✓ {h['title']}")

    # Upcoming
    upcoming = briefing["upcoming"]
    console.print(f"\n[bold]Next Week:[/bold] {upcoming['tasks_due']} tasks due")

    if upcoming["by_day"]:
        for day, tasks in upcoming["by_day"].items():
            console.print(f"  {day}: {len(tasks)} task(s)")

    # Insights
    if briefing["insights"]:
        console.print("\n[bold]Insights:[/bold]")
        for insight in briefing["insights"]:
            console.print(f"  💡 {insight}")

    console.print()


# Energy and context
@main.command()
@click.argument("level", type=click.Choice(["peak", "good", "low", "depleted"]))
@click.option("--note", "-n", default="", help="Optional note")
def energy(level, note):
    """Set current energy level."""
    ctx = aether.energy(level, note)
    emoji_map = {
        "peak": "⚡",
        "good": "✨",
        "low": "🔋",
        "depleted": "😴",
    }
    console.print(f"{emoji_map[level]} Energy set to: {level}")


@main.command()
def focus():
    """Toggle focus mode."""
    ctx = aether.context.get_current()
    new_state = not ctx.focus_mode
    aether.focus(new_state)
    if new_state:
        console.print("[bold]🎯 Focus mode ON[/bold]")
    else:
        console.print("[dim]Focus mode off[/dim]")


@main.command(name="break")
def take_break():
    """Record taking a break."""
    aether.take_break()
    console.print("☕ Break recorded. Take your time!")


# Reminders
@main.command()
@click.argument("title", nargs=-1, required=True)
@click.option("--at", "when", required=True, help="When to remind (HH:MM or datetime)")
@click.option("--adaptive", is_flag=True, help="Use adaptive timing")
def remind(title, when, adaptive):
    """Add a reminder."""
    title_text = " ".join(title)

    # Parse time
    try:
        if ":" in when and len(when) <= 5:
            # Just time, assume today
            hour, minute = map(int, when.split(":"))
            trigger = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            if trigger < datetime.now():
                trigger += timedelta(days=1)
        else:
            trigger = datetime.fromisoformat(when)
    except ValueError:
        console.print("[red]Invalid time format. Use HH:MM or ISO datetime.[/red]")
        return

    reminder = aether.remind(title_text, trigger, adaptive=adaptive)
    console.print(f"[green]✓[/green] Reminder set: {title_text}")
    console.print(f"  At: {trigger.strftime('%Y-%m-%d %H:%M')}")


@main.command(name="med")
@click.argument("name")
@click.option("--at", "when", required=True, help="Target time (HH:MM)")
@click.option("--window", "-w", default=2.0, help="Window in hours")
@click.option("--daily", is_flag=True, help="Repeat daily")
def medication(name, when, window, daily):
    """Add medication reminder with adaptive timing."""
    try:
        hour, minute = map(int, when.split(":"))
        trigger = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if trigger < datetime.now():
            trigger += timedelta(days=1)
    except ValueError:
        console.print("[red]Invalid time format. Use HH:MM.[/red]")
        return

    recurrence = "0 {} * * *".format(hour) if daily else None
    reminder = aether.medication(name, trigger, window, recurrence)

    console.print(f"[green]✓[/green] Medication reminder: {name}")
    console.print(f"  Target: {when} (±{window}h window)")
    if daily:
        console.print("  Repeats daily")


@main.command()
def reminders():
    """Show upcoming reminders."""
    upcoming = aether.reminders.get_upcoming(hours=24)

    if not upcoming:
        console.print("[dim]No upcoming reminders in the next 24 hours.[/dim]")
        return

    table = Table(title="Upcoming Reminders", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=8)
    table.add_column("Time", width=10)
    table.add_column("Reminder", min_width=30)
    table.add_column("Type", width=12)

    for r in upcoming:
        time_str = r.trigger_at.strftime("%H:%M") if r.trigger_at else "flexible"
        table.add_row(r.id, time_str, r.title, r.reminder_type.value)

    console.print(table)


@main.command()
@click.argument("reminder_id")
@click.option("--minutes", "-m", default=15, help="Snooze duration")
def snooze(reminder_id, minutes):
    """Snooze a reminder."""
    reminder = aether.snooze(reminder_id, minutes)
    if reminder:
        console.print(f"[yellow]💤[/yellow] Snoozed for {minutes} minutes")
    else:
        console.print("[red]Reminder not found or max snoozes reached[/red]")


@main.command()
@click.argument("reminder_id")
def ack(reminder_id):
    """Acknowledge/complete a reminder."""
    reminder = aether.ack(reminder_id)
    if reminder:
        console.print(f"[green]✓[/green] Acknowledged: {reminder.title}")
    else:
        console.print("[red]Reminder not found[/red]")


# Memory
@main.command()
@click.argument("key")
@click.argument("value", nargs=-1, required=True)
def remember(key, value):
    """Remember something for later."""
    value_text = " ".join(value)
    aether.remember(key, value_text)
    console.print(f"[green]✓[/green] Remembered: {key}")


@main.command()
@click.argument("key")
def recall(key):
    """Recall a stored memory."""
    value = aether.recall(key)
    if value:
        console.print(f"[bold]{key}:[/bold] {value}")
    else:
        console.print(f"[dim]No memory found for: {key}[/dim]")


# Analytics
@main.command()
def workload():
    """Analyze current workload."""
    analysis = aether.workload()

    console.print()
    console.print(Panel(
        f"Active: {analysis['total_active']} | "
        f"Overdue: {analysis['overdue']} | "
        f"Due today: {analysis['due_today']} | "
        f"Blocked: {analysis['blocked']}",
        title="Workload Analysis",
        box=box.ROUNDED,
    ))

    if analysis["by_area"]:
        console.print("\n[bold]By Area:[/bold]")
        for area, count in sorted(analysis["by_area"].items(), key=lambda x: -x[1]):
            console.print(f"  {area}: {count}")

    if analysis["by_priority"]:
        console.print("\n[bold]By Priority:[/bold]")
        for priority, count in analysis["by_priority"].items():
            console.print(f"  {priority}: {count}")

    if analysis["estimated_hours"] > 0:
        console.print(f"\n[bold]Estimated work:[/bold] {analysis['estimated_hours']:.1f} hours")

    if analysis["insights"]:
        console.print("\n[bold]Insights:[/bold]")
        for insight in analysis["insights"]:
            console.print(f"  {insight}")

    console.print()


@main.command()
def productivity():
    """Show today's productivity score."""
    score = aether.productivity()

    console.print()
    console.print(Panel(
        f"[bold]Score: {score['score']}/100[/bold]\n\n"
        f"Tasks completed: {score['tasks_completed']}\n"
        f"Estimated time: {score['estimated_minutes']}min\n"
        f"Actual time: {score['actual_minutes']}min\n"
        f"Breaks taken: {score['breaks_taken']}\n"
        f"Current energy: {score['current_energy']}",
        title="Today's Productivity",
        box=box.ROUNDED,
    ))
    console.print()


@main.command()
def stats():
    """Show overall statistics."""
    s = aether.stats()

    console.print()
    console.print("[bold]Tasks:[/bold]")
    console.print(f"  Total: {s['tasks']['total']} | Done: {s['tasks']['done']} | "
                  f"Active: {s['tasks']['active']} | Overdue: {s['tasks']['overdue']}")

    console.print(f"\n[bold]Reminders:[/bold]")
    console.print(f"  Total: {s['reminders']['total']} | Active: {s['reminders']['active']}")

    console.print(f"\n[bold]Events:[/bold]")
    console.print(f"  Total: {s['events']['total']} | Upcoming: {s['events']['upcoming']}")

    console.print(f"\n[bold]Memories:[/bold] {s['memories']['total']}")

    console.print(f"\n[bold]Patterns:[/bold] {s['patterns']['total']} "
                  f"(avg confidence: {s['patterns']['avg_confidence'] or 0:.2f})")
    console.print()


# Areas and projects
@main.command()
def areas():
    """List all areas."""
    area_list = aether.areas()
    if area_list:
        console.print("[bold]Areas:[/bold]")
        for a in area_list:
            count = len(aether.by_area(a))
            console.print(f"  {a}: {count} tasks")
    else:
        console.print("[dim]No areas defined yet.[/dim]")


@main.command()
def projects():
    """List all projects."""
    project_list = aether.projects()
    if project_list:
        console.print("[bold]Projects:[/bold]")
        for p in project_list:
            count = len(aether.by_project(p))
            console.print(f"  {p}: {count} tasks")
    else:
        console.print("[dim]No projects defined yet.[/dim]")


@main.command()
@click.argument("name")
@click.option("--type", "filter_type", type=click.Choice(["area", "project"]), default="area")
def show(name, filter_type):
    """Show tasks for an area or project."""
    if filter_type == "area":
        tasks = aether.by_area(name)
        title = f"Area: {name}"
    else:
        tasks = aether.by_project(name)
        title = f"Project: {name}"

    print_tasks_table(tasks, title)


# Server
@main.command()
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8080, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host, port, reload):
    """Start the Aether web server."""
    import uvicorn
    from .web.server import create_app

    console.print(f"[bold]Starting Aether server...[/bold]")
    console.print(f"  URL: http://{host}:{port}")
    console.print(f"  API: http://{host}:{port}/api")
    console.print()

    app = create_app()
    uvicorn.run(
        "aether.web.server:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


# Setup wizard
@main.command()
def setup():
    """Interactive setup wizard."""
    import yaml
    from pathlib import Path

    console.print("[bold]Aether Setup Wizard[/bold]\n")

    config = {}

    # Todoist
    console.print("[bold]1. Todoist Integration[/bold]")
    todoist_token = click.prompt("  Todoist API token (or press Enter to skip)", default="", show_default=False)
    if todoist_token:
        config["todoist"] = {"api_token": todoist_token}

    # Home Assistant
    console.print("\n[bold]2. Home Assistant Integration[/bold]")
    ha_url = click.prompt("  Home Assistant URL (or press Enter to skip)", default="", show_default=False)
    if ha_url:
        ha_token = click.prompt("  Long-lived access token")
        config["homeassistant"] = {"url": ha_url, "token": ha_token}

    # Save config
    config_dir = Path.home() / ".aether"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    console.print(f"\n[green]✓[/green] Configuration saved to {config_path}")
    console.print("\nNext steps:")
    console.print("  1. Run 'aether serve' to start the web server")
    console.print("  2. Access the UI at http://localhost:8080")
    console.print("  3. Install the PWA on your phone for mobile access")


# Chores
@main.command()
def chores():
    """List chores."""
    from .chores import ChoreManager

    chore_mgr = ChoreManager(aether.store)
    chore_list = chore_mgr.get_due()

    if not chore_list:
        console.print("[dim]No chores due.[/dim]")
        return

    table = Table(title="Chores Due", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=8)
    table.add_column("Chore", min_width=25)
    table.add_column("Room", width=12)
    table.add_column("Time", width=8)
    table.add_column("Status", width=12)

    for c in chore_list:
        status = "Overdue" if c.is_overdue else f"{c.days_until_due}d"
        table.add_row(
            c.id,
            c.name,
            c.room or "-",
            f"{c.duration_minutes}m",
            status,
        )

    console.print(table)


@main.command()
@click.argument("chore_id")
def chore_done(chore_id):
    """Mark a chore as done."""
    from .chores import ChoreManager

    chore_mgr = ChoreManager(aether.store)
    chore = chore_mgr.complete(chore_id)

    if chore:
        streak_msg = f" 🔥 {chore.streak} streak!" if chore.streak > 1 else ""
        console.print(f"[green]✓[/green] Completed: {chore.name}{streak_msg}")
    else:
        console.print(f"[red]✗[/red] Chore not found: {chore_id}")


# Sync
@main.command()
def sync():
    """Sync with external services."""
    import asyncio

    console.print("[bold]Syncing...[/bold]")

    # Load config
    from pathlib import Path
    import yaml

    config_path = Path.home() / ".aether" / "config.yaml"
    if not config_path.exists():
        console.print("[yellow]No config found. Run 'aether setup' first.[/yellow]")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    # Todoist sync
    if "todoist" in config:
        from .integrations.todoist import TodoistSync

        todoist = TodoistSync(config["todoist"]["api_token"], aether.store)
        result = todoist.sync_blocking()
        console.print(f"  Todoist: {result['synced']} tasks synced, {result['created']} new")

    console.print("[green]✓[/green] Sync complete")


if __name__ == "__main__":
    main()
