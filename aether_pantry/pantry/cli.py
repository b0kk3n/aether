"""Command-line interface for Aether Pantry."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from pantry import __version__

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """Aether Pantry.

    What's low or out at home, so it doesn't have to live in your head.
    """
    pass


@main.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8100, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the Aether Pantry web server."""
    import uvicorn
    console.print(f"[bold green]Starting Aether Pantry on http://{host}:{port}[/bold green]")
    uvicorn.run(
        "pantry.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@main.command()
def products():
    """List all products with their status."""
    from pantry.core import ProductService

    items = ProductService.get_all()
    if not items:
        console.print("[dim]No products yet.[/dim]")
        return

    table = Table(title="Products")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Status", justify="center")

    for p in items:
        color = {"in_stock": "green", "low": "yellow", "out": "red"}[p.effective_status.value]
        table.add_row(p.id, p.name, p.category_name or "-", f"[{color}]{p.effective_status.value}[/{color}]")

    console.print(table)


@main.group()
def grocery():
    """Manage the grocery list."""
    pass


@grocery.command("add")
@click.argument("text")
def grocery_add(text: str):
    """Add a line to the grocery list."""
    from pantry.core import GroceryListService

    item = GroceryListService.add_item(text)
    if item.is_linked:
        console.print(f"[green]Added (linked to {item.linked_product_name}):[/green] {item.raw_text}")
    else:
        console.print(f"[green]Added:[/green] {item.raw_text}")


@grocery.command("list")
def grocery_list():
    """Show the current grocery list."""
    from pantry.core import GroceryListService

    items = GroceryListService.get_all()
    if not items:
        console.print("[dim]Grocery list is empty.[/dim]")
        return

    for item in items:
        tag = f"[cyan]linked[/cyan]" if item.is_linked else "[dim]free text[/dim]"
        console.print(f"  · {item.raw_text} ({tag})")


@grocery.command("check-off")
@click.argument("item_id")
def grocery_check_off(item_id: str):
    """Check off a grocery list line."""
    from pantry.core import GroceryListService

    if GroceryListService.check_off(item_id):
        console.print("[green]Checked off.[/green]")
    else:
        console.print(f"[red]Item not found: {item_id}[/red]")


@main.command()
def checklists():
    """List all checklists."""
    from pantry.core import ChecklistService

    lists = ChecklistService.get_all()
    if not lists:
        console.print("[dim]No checklists yet.[/dim]")
        return

    table = Table(title="Checklists")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Out", justify="center", style="red")
    table.add_column("Low", justify="center", style="yellow")
    table.add_column("In Stock", justify="center", style="green")

    for cl in lists:
        table.add_row(cl.id, f"{cl.icon} {cl.name}", str(cl.out_count), str(cl.low_count), str(cl.in_stock_count))

    console.print(table)


@main.group()
def vacation():
    """Manage vacation mode."""
    pass


@vacation.command("start")
def vacation_start():
    """Start vacation mode, freezing every product's interval clock."""
    from pantry.core import VacationService

    try:
        VacationService.start()
        console.print("[green]Vacation mode started.[/green] Interval clocks are now paused.")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@vacation.command("end")
def vacation_end():
    """End vacation mode, shifting products' next_due forward."""
    from pantry.core import VacationService

    try:
        result = VacationService.end()
        days = round(result.days_elapsed, 1)
        console.print(
            f"[green]Welcome back![/green] {result.products_affected} product(s) shifted forward by ~{days} day(s)."
        )
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@vacation.command("status")
def vacation_status():
    """Show current vacation mode status."""
    from pantry.core import VacationService

    status = VacationService.get_status()
    if status.is_active:
        days = round(status.days_elapsed, 1)
        console.print(f"[green]Vacation mode is active[/green] — {days} day(s) so far.")
    else:
        console.print("[dim]Vacation mode is not active.[/dim]")


if __name__ == "__main__":
    main()
