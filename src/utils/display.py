"""Utility functions for the application."""

from typing import Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.models import ProteinTarget

console = Console()


def display_results(targets: list[ProteinTarget], max_display: int = 10):
    """Display ranked protein targets in a formatted table."""
    
    console.print("\n")
    console.print(Panel.fit(
        f"[bold cyan]Protein Target Discovery Results[/bold cyan]\n"
        f"Found {len(targets)} potential targets",
        border_style="cyan"
    ))
    
    # Create table
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Gene", style="cyan", width=10)
    table.add_column("Protein Name", width=30)
    table.add_column("Overall\nScore", justify="right", width=8)
    table.add_column("Genetic", justify="right", width=8)
    table.add_column("Literature", justify="right", width=10)
    table.add_column("Structural", justify="right", width=10)
    table.add_column("Sources", width=15)
    
    # Add rows
    for idx, target in enumerate(targets[:max_display], 1):
        # Color code overall score
        score = target.overall_score
        if score >= 0.8:
            score_str = f"[green]{score:.3f}[/green]"
        elif score >= 0.6:
            score_str = f"[yellow]{score:.3f}[/yellow]"
        else:
            score_str = f"[red]{score:.3f}[/red]"
        
        table.add_row(
            str(idx),
            target.gene_symbol,
            target.protein_name[:28] + "..." if len(target.protein_name) > 30 else target.protein_name,
            score_str,
            f"{target.genetic_score:.2f}",
            f"{target.literature_score:.2f}",
            f"{target.structural_score:.2f}",
            ", ".join(target.evidence_sources[:2])
        )
    
    console.print(table)
    
    # Show detailed info for top target
    if targets:
        top_target = targets[0]
        console.print("\n[bold]Top Target Details:[/bold]")
        console.print(f"  Gene: [cyan]{top_target.gene_symbol}[/cyan]")
        console.print(f"  Protein: {top_target.protein_name}")
        console.print(f"  Overall Score: [green]{top_target.overall_score:.3f}[/green]")
        console.print(f"  Evidence Sources: {', '.join(top_target.evidence_sources)}")
        
        if top_target.key_findings:
            console.print("\n  [bold]Key Findings:[/bold]")
            for finding in top_target.key_findings[:3]:
                console.print(f"    • {finding}")
    
    console.print("\n")


def export_to_csv(targets: list[ProteinTarget], filename: str):
    """Export ranked targets to CSV file."""
    import csv
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Rank", "Gene", "Protein Name", "Overall Score",
            "Genetic Score", "Literature Score", "Structural Score",
            "Druggability Score", "Evidence Sources", "Key Findings"
        ])
        
        for idx, target in enumerate(targets, 1):
            writer.writerow([
                idx,
                target.gene_symbol,
                target.protein_name,
                f"{target.overall_score:.3f}",
                f"{target.genetic_score:.3f}",
                f"{target.literature_score:.3f}",
                f"{target.structural_score:.3f}",
                f"{target.druggability_score:.3f}",
                "; ".join(target.evidence_sources),
                "; ".join(target.key_findings)
            ])
    
    console.print(f"[green]✓[/green] Results exported to {filename}")
