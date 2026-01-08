"""Main CLI entry point for the agentic target discovery application."""

import typer
from rich.console import Console
from typing import Optional

from src.agents import run_target_discovery
from src.utils import display_results, export_to_csv

app = typer.Typer(help="Agentic Protein Target Discovery System")
console = Console()


@app.command()
def discover(
    disease: str = typer.Argument(..., help="Disease name to search for protein targets"),
    max_targets: int = typer.Option(10, "--max-targets", "-n", help="Maximum number of targets to display"),
    min_score: float = typer.Option(0.0, "--min-score", "-s", help="Minimum overall score threshold (0-1)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export results to CSV file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed progress"),
):
    """
    Discover and rank protein targets for a disease.
    
    Example:
        python main.py discover "Alzheimer's disease"
        python main.py discover "Type 2 diabetes" --max-targets 20 --output results.csv
    """
    console.print(f"\n[bold cyan]🔬 Discovering protein targets for:[/bold cyan] {disease}\n")
    
    try:
        # Run the agent
        with console.status("[bold green]Searching databases..."):
            state = run_target_discovery(disease, verbose=verbose)
        
        print(state)
        # Filter by minimum score
        filtered_targets = [
            t for t in state['ranked_targets']
            if t.overall_score >= min_score
        ]
        
        if not filtered_targets:
            console.print(f"[yellow]No targets found meeting minimum score threshold of {min_score}[/yellow]")
            return
        
        # Display results
        display_results(filtered_targets, max_display=max_targets)
        
        # Export if requested
        if output:
            export_to_csv(filtered_targets, output)
        
        console.print(f"[green]✓[/green] Discovery complete! Found {len(filtered_targets)} targets.\n")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            raise


@app.command()
def config():
    """Show current configuration and check API keys."""
    from src.config import settings
    
    console.print("\n[bold]Configuration Status:[/bold]\n")
    
    # LLM provider
    try:
        provider = settings.get_llm_provider()
        console.print(f"  LLM Provider: [green]{provider}[/green]")
        console.print(f"  Model: {settings.llm_model}")
    except ValueError as e:
        console.print(f"  LLM Provider: [red]Not configured[/red]")
        console.print(f"    {e}")
    
    # NCBI
    if settings.ncbi_api_key:
        console.print(f"  NCBI API Key: [green]✓ Configured[/green]")
    else:
        console.print(f"  NCBI API Key: [yellow]⚠ Not set (limited rate)[/yellow]")
    
    console.print(f"\n  Max PubMed Results: {settings.max_pubmed_results}")
    console.print(f"  Max GWAS Results: {settings.max_gwas_results}")
    console.print()


if __name__ == "__main__":
    app()
