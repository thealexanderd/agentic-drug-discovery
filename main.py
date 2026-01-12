"""Main CLI entry point for the agentic target discovery application."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional

from src.agents import run_target_discovery
from src.utils import display_results, export_to_csv

app = typer.Typer(help="Agentic Protein Target Discovery System")
console = Console()


def display_reasoning_trace(state: dict):
    """Display the agent's reasoning trace."""
    console.print("\n[bold cyan]📋 Agent Reasoning Trace[/bold cyan]\n")
    
    for step in state.get("reasoning_trace", []):
        icon = {
            "plan": "🎯",
            "analyze": "🔍",
            "decide": "🤔",
            "synthesize": "🧬",
            "search": "🔎"
        }.get(step.action_type, "•")
        
        console.print(f"  {icon} [bold]Step {step.step_number}[/bold] ({step.action_type})")
        console.print(f"     {step.description}")
        if step.output:
            console.print(f"     [dim]→ {step.output[:100]}...[/dim]" if len(step.output) > 100 else f"     [dim]→ {step.output}[/dim]")
        console.print()


def display_research_plan(state: dict):
    """Display the agent's research plan."""
    plan = state.get("research_plan")
    if not plan:
        return
    
    console.print("\n[bold cyan]🎯 Research Plan[/bold cyan]\n")
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold")
    table.add_column("Value")
    
    table.add_row("Disease", plan.disease_name)
    table.add_row("Type", plan.disease_type)
    table.add_row("Strategy", plan.search_strategy[:100] + "..." if len(plan.search_strategy) > 100 else plan.search_strategy)
    
    if plan.key_hypotheses:
        table.add_row("Hypotheses", "\n".join(f"• {h}" for h in plan.key_hypotheses[:3]))
    
    if plan.priority_pathways:
        table.add_row("Key Pathways", ", ".join(plan.priority_pathways[:4]))
    
    console.print(table)
    console.print()


def display_intermediate_analyses(state: dict):
    """Display intermediate analysis summaries."""
    analyses = state.get("intermediate_analyses", [])
    if not analyses:
        return
    
    console.print("\n[bold cyan]🔍 Database Search Results[/bold cyan]\n")
    
    for analysis in analyses:
        confidence_color = {
            "high": "green",
            "medium": "yellow",
            "low": "red"
        }.get(analysis.confidence_level, "white")
        
        console.print(f"  [{confidence_color}]■[/{confidence_color}] [bold]{analysis.tool_used.upper()}[/bold]")
        console.print(f"     {analysis.results_summary[:120]}..." if len(analysis.results_summary) > 120 else f"     {analysis.results_summary}")
        if analysis.key_proteins_found:
            console.print(f"     [dim]Proteins: {', '.join(analysis.key_proteins_found[:5])}[/dim]")
        console.print()


def display_final_synthesis(state: dict):
    """Display the LLM's final synthesis."""
    synthesis = state.get("final_synthesis", "")
    if synthesis:
        console.print("\n[bold cyan]🧬 AI Synthesis[/bold cyan]\n")
        console.print(Panel(
            Markdown(synthesis),
            border_style="cyan",
            padding=(1, 2)
        ))


def display_target_details(targets: list, max_display: int = 5):
    """Display detailed target information with LLM insights."""
    console.print("\n[bold cyan]🎯 Top Protein Targets[/bold cyan]\n")
    
    for i, target in enumerate(targets[:max_display], 1):
        # Create target panel
        score_bar = "█" * int(target.overall_score * 20) + "░" * (20 - int(target.overall_score * 20))
        
        console.print(f"\n[bold white]#{i}. {target.gene_symbol}[/bold white] - {target.protein_name}")
        console.print(f"    Score: [{score_bar}] {target.overall_score:.2f}")
        console.print(f"    Sources: {', '.join(target.evidence_sources)}")
        
        # Show individual scores
        scores = []
        if target.disgenet_score > 0:
            scores.append(f"DisGeNET: {target.disgenet_score:.2f}")
        if target.genetic_score > 0:
            scores.append(f"Genetic: {target.genetic_score:.2f}")
        if target.literature_score > 0:
            scores.append(f"Literature: {target.literature_score:.2f}")
        if target.go_score > 0:
            scores.append(f"GO: {target.go_score:.2f}")
        if target.pathway_score > 0:
            scores.append(f"Pathway: {target.pathway_score:.2f}")
        
        if scores:
            console.print(f"    [dim]Breakdown: {' | '.join(scores)}[/dim]")
        
        # Show pathways
        if target.related_pathways:
            console.print(f"    [dim]Pathways: {', '.join(target.related_pathways[:3])}[/dim]")
        
        # Show LLM synthesis if available
        if target.llm_synthesis:
            syn = target.llm_synthesis
            console.print(f"\n    [italic]{syn.overall_assessment[:200]}...[/italic]" 
                         if len(syn.overall_assessment) > 200 else f"\n    [italic]{syn.overall_assessment}[/italic]")
            console.print(f"    Evidence strength: [bold]{syn.strength_of_evidence}[/bold]")
        
        # Key findings
        if target.key_findings:
            console.print(f"    Key findings:")
            for finding in target.key_findings[:3]:
                console.print(f"      • {finding[:80]}...")


@app.command()
def discover(
    disease: str = typer.Argument(..., help="Disease name to search for protein targets"),
    max_targets: int = typer.Option(10, "--max-targets", "-n", help="Maximum number of targets to display"),
    min_score: float = typer.Option(0.0, "--min-score", "-s", help="Minimum overall score threshold (0-1)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export results to CSV file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed agent reasoning"),
    show_plan: bool = typer.Option(False, "--show-plan", "-p", help="Show the research plan"),
):
    """
    Discover and rank protein targets for a disease using agentic AI.
    
    The agent will:
    1. Analyze the disease and create a tailored research plan
    2. Dynamically search relevant databases
    3. Evaluate results and adjust strategy
    4. Synthesize evidence with AI reasoning
    
    Example:
        python main.py discover "Alzheimer's disease"
        python main.py discover "Type 2 diabetes" --verbose --show-plan
        python main.py discover "Systemic Lupus Erythematosus" --max-targets 20 --output results.csv
    """
    console.print(f"\n[bold cyan]🔬 Agentic Protein Target Discovery[/bold cyan]")
    console.print(f"[bold]Disease:[/bold] {disease}\n")
    
    try:
        # Run the agentic workflow
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Agent is researching...", total=None)
            state = run_target_discovery(disease, verbose=verbose)
        
        # Show research plan if requested
        if show_plan or verbose:
            display_research_plan(state)
        
        # Show intermediate analyses
        if verbose:
            display_intermediate_analyses(state)
            display_reasoning_trace(state)
        
        # Filter by minimum score
        filtered_targets = [
            t for t in state['ranked_targets']
            if t.overall_score >= min_score
        ]
        
        if not filtered_targets:
            console.print(f"[yellow]No targets found meeting minimum score threshold of {min_score}[/yellow]")
            return
        
        # Display detailed targets
        display_target_details(filtered_targets, max_display=max_targets)
        
        # Show final synthesis
        if verbose or show_plan:
            display_final_synthesis(state)
        
        # Also display in table format
        console.print("\n")
        display_results(filtered_targets, max_display=max_targets)
        
        # Export if requested
        if output:
            export_to_csv(filtered_targets, output)
            console.print(f"\n[green]✓[/green] Results exported to {output}")
        
        console.print(f"\n[green]✓[/green] Discovery complete! Found {len(filtered_targets)} targets.")
        console.print(f"   Databases queried: {', '.join(state.get('tools_executed', []))}")
        console.print(f"   Iterations: {state.get('iteration_count', 0)}")
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
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
    
    # DisGeNET
    if settings.disgenet_api_key:
        console.print(f"  DisGeNET API Key: [green]✓ Configured[/green]")
    else:
        console.print(f"  DisGeNET API Key: [yellow]⚠ Not set (limited access)[/yellow]")
    
    console.print(f"\n  Max Iterations: {settings.max_iterations}")
    console.print(f"  Max PubMed Results: {settings.max_pubmed_results}")
    console.print(f"  Max GWAS Results: {settings.max_gwas_results}")
    console.print(f"  Verbose Reasoning: {settings.verbose_reasoning}")
    console.print()


@app.command()
def tools():
    """Show available database tools and their purposes."""
    from src.tools import TOOL_REGISTRY
    
    console.print("\n[bold]Available Database Tools:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Tool", style="bold")
    table.add_column("Priority")
    table.add_column("Purpose")
    table.add_column("Best For")
    
    for tool_id, info in TOOL_REGISTRY.items():
        priority_color = {1: "green", 2: "yellow", 3: "dim"}.get(info["priority"], "white")
        priority_label = {1: "Core", 2: "Recommended", 3: "Supplementary"}.get(info["priority"], "Other")
        
        table.add_row(
            info["name"],
            f"[{priority_color}]{priority_label}[/{priority_color}]",
            info["purpose"][:50] + "..." if len(info["purpose"]) > 50 else info["purpose"],
            ", ".join(info["best_for"][:2])
        )
    
    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
