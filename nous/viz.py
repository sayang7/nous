"""Visualization for Nous reasoning graphs.

Three rendering surfaces:
  1. n.show()          → Pyvis interactive graph in browser
  2. _repr_html_()     → Jupyter inline rendering
  3. Rich terminal     → print(n.state()) with colored trees

All visualization dependencies are optional. Nous works without them.
If a dependency is missing, the method tells you how to install it.
"""

from __future__ import annotations

import html
import tempfile
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nous.graph import CommitmentGraph


def show_graph(graph: CommitmentGraph, path: Optional[str] = None) -> str:
    """Open an interactive graph visualization in the browser.

    Uses Pyvis (built on vis.js) for force-directed, interactive
    network graphs. Nodes are clickable, zoomable, draggable.

    Violations glow red. Explicit assertions are blue.
    Derived commitments are lighter. Edges show entailment rules.

    Args:
        graph: The CommitmentGraph to visualize.
        path: Optional file path to write HTML. If None, uses tempfile.

    Returns:
        Path to the generated HTML file.
    """
    try:
        from pyvis.network import Network
    except ImportError:
        raise ImportError(
            "Visualization requires pyvis. Install with:\n"
            "  pip install nous-ai[viz]\n"
            "Or: pip install pyvis"
        )

    net = Network(
        height="750px",
        width="100%",
        directed=True,
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
    )
    net.set_options("""
    {
      "nodes": {
        "font": {"size": 12, "face": "monospace"},
        "borderWidth": 2,
        "shadow": true
      },
      "edges": {
        "arrows": {"to": {"enabled": true, "scaleFactor": 0.8}},
        "color": {"inherit": false},
        "font": {"size": 9, "face": "monospace", "color": "#888888"},
        "smooth": {"type": "curvedCW", "roundness": 0.2}
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 200
        },
        "solver": "forceAtlas2Based",
        "stabilization": {"iterations": 100}
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100
      }
    }
    """)

    # Color scheme
    violated_contents = {v.violated_node.content for v in graph.violations}

    for content, node in graph.nodes.items():
        label = content[:80] + "..." if len(content) > 80 else content
        title = f"Step {node.source_step} | {node.modality}"

        if content in violated_contents:
            color = "#ff4444"
            border_color = "#ff0000"
            title += " | VIOLATED"
        elif node.is_explicit:
            color = "#4a90d9"
            border_color = "#2a70b9"
        else:
            color = "#6a6a8a"
            border_color = "#4a4a6a"

        net.add_node(
            content,
            label=label,
            title=title,
            color={"background": color, "border": border_color},
            shape="box",
            font={"color": "#ffffff"},
        )

    for edge in graph.edges:
        p, c = edge.premise.content, edge.consequence.content
        if p in graph.nodes and c in graph.nodes:
            edge_color = "#ff6666" if c in violated_contents else "#555588"
            net.add_edge(
                p, c,
                title=f"{edge.rule} ({edge.confidence:.2f})",
                label=edge.rule,
                color=edge_color,
                width=max(1, edge.confidence * 3),
            )

    # Write to file
    if path is None:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".html", prefix="nous_graph_", delete=False,
        )
        path = tmp.name
        tmp.close()

    net.save_graph(path)
    return path


def open_in_browser(path: str) -> None:
    """Open an HTML file in the default browser."""
    try:
        webbrowser.open(f"file://{Path(path).resolve()}")
    except Exception:
        print(f"Could not open browser. View the graph at: {path}")


def graph_to_html(graph: CommitmentGraph) -> str:
    """Generate an inline HTML representation for Jupyter notebooks.

    Returns an HTML string that can be used as _repr_html_ output.
    Uses a simple SVG-based visualization for inline rendering.
    """
    if not graph.nodes:
        return "<div style='color:#888; padding:10px;'>Empty reasoning graph</div>"

    violated_contents = {v.violated_node.content for v in graph.violations}

    rows = []
    for content, node in graph.nodes.items():
        escaped = html.escape(content[:100])
        if content in violated_contents:
            color = "#ff4444"
            badge = " <span style='color:#ff4444;font-weight:bold;'>[VIOLATED]</span>"
        elif node.is_explicit:
            color = "#4a90d9"
            badge = " <span style='color:#4a90d9;'>[explicit]</span>"
        else:
            color = "#6a6a8a"
            badge = " <span style='color:#6a6a8a;'>[derived]</span>"

        rows.append(
            f"<tr><td style='border-left:3px solid {color};padding:4px 8px;'>"
            f"<code>{escaped}</code>{badge}</td>"
            f"<td style='padding:4px 8px;color:#888;'>step {node.source_step}</td></tr>"
        )

    edge_rows = []
    for edge in graph.edges:
        p = html.escape(edge.premise.content[:50])
        c = html.escape(edge.consequence.content[:50])
        edge_rows.append(
            f"<tr><td style='padding:2px 8px;'><code>{p}</code></td>"
            f"<td style='padding:2px 8px;'>→</td>"
            f"<td style='padding:2px 8px;'><code>{c}</code></td>"
            f"<td style='padding:2px 8px;color:#888;'>{edge.rule} ({edge.confidence:.2f})</td></tr>"
        )

    closure_size = len(graph.get_closure())
    violation_count = len(graph.violations)

    summary_color = "#ff4444" if violation_count > 0 else "#4a90d9"

    return f"""
    <div style='font-family:monospace; background:#1a1a2e; color:#e0e0e0; padding:12px; border-radius:8px; margin:8px 0;'>
      <div style='font-size:14px; font-weight:bold; color:{summary_color}; margin-bottom:8px;'>
        Nous — {len(graph.nodes)} commitments, {len(graph.edges)} edges, {closure_size} in closure, {violation_count} violations
      </div>
      <table style='width:100%; border-collapse:collapse;'>
        {"".join(rows)}
      </table>
      {"<div style='margin-top:8px; font-size:12px; color:#888;'>Edges:</div><table style='width:100%; border-collapse:collapse; font-size:11px;'>" + "".join(edge_rows) + "</table>" if edge_rows else ""}
    </div>
    """


def rich_print_state(graph: CommitmentGraph) -> str:
    """Generate a Rich-formatted string for terminal output.

    Falls back to plain text if Rich is not installed.
    """
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.tree import Tree
        from rich.text import Text
        import io

        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=100)

        violated_contents = {v.violated_node.content for v in graph.violations}
        closure = graph.get_closure()

        # Header
        violation_count = len(graph.violations)
        if violation_count > 0:
            header = Text(f"Nous — {violation_count} violation(s) detected", style="bold red")
        else:
            header = Text("Nous — reasoning coherent", style="bold green")
        console.print(header)

        # Commitments tree
        tree = Tree("[bold]Commitments[/bold]")
        for content, node in graph.nodes.items():
            if content in violated_contents:
                style = "red bold"
                prefix = "[!] "
            elif node.is_explicit:
                style = "cyan"
                prefix = "[+] "
            else:
                style = "dim"
                prefix = "    "
            label = content[:80] + "..." if len(content) > 80 else content
            tree.add(f"{prefix}[{style}]{label}[/{style}] (step {node.source_step})")

        console.print(tree)

        # Violations
        if graph.violations:
            console.print()
            for v in graph.violations:
                console.print(f"[red bold]VIOLATION[/red bold] at step {v.action_step}: {v.violation_type}")
                console.print(f"  Action: {v.action}")
                console.print(f"  Violated: {v.violated_node.content}")
                console.print(f"  Confidence: {v.confidence:.0%}")

        # Stats
        console.print()
        console.print(
            f"[dim]{len(graph.nodes)} nodes, {len(graph.edges)} edges, "
            f"{len(closure)} in closure[/dim]"
        )

        return buf.getvalue()

    except ImportError:
        # Fallback: plain text
        return _plain_text_state(graph)


def _plain_text_state(graph: CommitmentGraph) -> str:
    """Plain text fallback when Rich is not installed."""
    lines = []
    violated_contents = {v.violated_node.content for v in graph.violations}
    closure = graph.get_closure()

    violation_count = len(graph.violations)
    if violation_count > 0:
        lines.append(f"Nous — {violation_count} violation(s) detected")
    else:
        lines.append("Nous — reasoning coherent")
    lines.append("")

    lines.append("Commitments:")
    for content, node in graph.nodes.items():
        if content in violated_contents:
            prefix = "[!] "
        elif node.is_explicit:
            prefix = "[+] "
        else:
            prefix = "    "
        label = content[:80] + "..." if len(content) > 80 else content
        lines.append(f"  {prefix}{label} (step {node.source_step})")

    if graph.violations:
        lines.append("")
        for v in graph.violations:
            lines.append(f"VIOLATION at step {v.action_step}: {v.violation_type}")
            lines.append(f"  Action: {v.action}")
            lines.append(f"  Violated: {v.violated_node.content}")
            lines.append(f"  Confidence: {v.confidence:.0%}")

    lines.append("")
    lines.append(
        f"{len(graph.nodes)} nodes, {len(graph.edges)} edges, "
        f"{len(closure)} in closure"
    )
    return "\n".join(lines)
