"""Tool initialization and exports."""

from src.tools.pubmed_tool import create_pubmed_tool, PubMedTool
from src.tools.gwas_tool import create_gwas_tool, GWASTool
from src.tools.uniprot_tool import create_uniprot_tool, UniProtTool
from src.tools.pdb_tool import create_pdb_tool, PDBTool
from src.tools.pubchem_tool import create_pubchem_tool, PubChemTool
from src.tools.disgenet_tool import create_disgenet_tool, DisGeNETTool
from src.tools.go_tool import create_go_tool, GOTool
from src.tools.reactome_tool import create_reactome_tool, ReactomeTool
from src.tools.opentargets_mcp_tool import create_opentargets_mcp_tool, OpenTargetsMCPTool

__all__ = [
    # Core mandatory tools
    "create_pubmed_tool",
    "create_uniprot_tool",
    "create_disgenet_tool",
    "create_go_tool",
    # Strongly recommended tools
    "create_gwas_tool",
    "create_reactome_tool",
    "create_opentargets_mcp_tool",
    # Supplementary tools
    "create_pdb_tool",
    "create_pubchem_tool",
    # Tool classes
    "PubMedTool",
    "GWASTool",
    "UniProtTool",
    "PDBTool",
    "PubChemTool",
    "DisGeNETTool",
    "GOTool",
    "ReactomeTool",
    "OpenTargetsMCPTool",
]

# Tool registry with metadata for agentic selection
TOOL_REGISTRY = {
    "pubmed": {
        "name": "PubMed",
        "purpose": "Mechanistic and experimental evidence from literature",
        "priority": 1,  # Core mandatory
        "provides": ["literature_evidence", "protein_mentions", "pmids"],
        "best_for": ["mechanistic understanding", "experimental validation", "therapeutic context"],
        "limitations": ["high noise", "requires filtering"],
        "factory": create_pubmed_tool
    },
    "uniprot": {
        "name": "UniProt",
        "purpose": "Protein identity, function, and cross-references",
        "priority": 1,  # Core mandatory
        "provides": ["protein_info", "function", "disease_annotations", "pdb_refs"],
        "best_for": ["protein validation", "functional context", "canonical definitions"],
        "limitations": ["may miss novel associations"],
        "factory": create_uniprot_tool
    },
    "disgenet": {
        "name": "DisGeNET",
        "purpose": "Curated gene-disease associations with scores",
        "priority": 1,  # Core mandatory
        "provides": ["gene_disease_scores", "evidence_counts", "snp_associations"],
        "best_for": ["disease-gene validation", "ranking", "evidence strength"],
        "limitations": ["may have curation lag"],
        "factory": create_disgenet_tool
    },
    "go": {
        "name": "Gene Ontology",
        "purpose": "Biological function and process validation",
        "priority": 1,  # Core mandatory
        "provides": ["biological_processes", "molecular_functions", "cellular_components"],
        "best_for": ["mechanism validation", "functional relevance", "pathway context"],
        "limitations": ["annotation completeness varies"],
        "factory": create_go_tool
    },
    "gwas": {
        "name": "GWAS Catalog",
        "purpose": "Genetic association evidence",
        "priority": 2,  # Strongly recommended
        "provides": ["genetic_associations", "p_values", "risk_alleles"],
        "best_for": ["genetic diseases", "causal evidence", "novel targets"],
        "limitations": ["only for diseases with genetic studies"],
        "factory": create_gwas_tool
    },
    "reactome": {
        "name": "Reactome",
        "purpose": "Pathway context and clustering",
        "priority": 2,  # Strongly recommended
        "provides": ["pathway_membership", "pathway_enrichment", "mechanism_context"],
        "best_for": ["pathway analysis", "target clustering", "mechanistic explanation"],
        "limitations": ["pathway coverage varies"],
        "factory": create_reactome_tool
    },
    "opentargets": {
        "name": "OpenTargets (MCP)",
        "purpose": "Comprehensive multi-source target-disease evidence",
        "priority": 2,  # Strongly recommended
        "provides": ["target_disease_scores", "evidence_by_datatype", "drug_info", "genetics", "pathways"],
        "best_for": ["comprehensive evidence", "target prioritization", "multi-source integration", "known drugs"],
        "limitations": ["may be slower", "requires disease ID mapping"],
        "factory": create_opentargets_mcp_tool
    },
    "pdb": {
        "name": "PDB",
        "purpose": "Structural data for druggability assessment",
        "priority": 3,  # Supplementary
        "provides": ["3d_structures", "binding_sites", "structural_coverage"],
        "best_for": ["druggability assessment", "structure-based design"],
        "limitations": ["not all proteins have structures"],
        "factory": create_pdb_tool
    },
    "pubchem": {
        "name": "PubChem",
        "purpose": "Existing compounds and druggability",
        "priority": 3,  # Supplementary
        "provides": ["known_ligands", "bioactivity_data", "compound_info"],
        "best_for": ["druggability validation", "existing drugs", "repurposing"],
        "limitations": ["limited to known compounds"],
        "factory": create_pubchem_tool
    }
}
