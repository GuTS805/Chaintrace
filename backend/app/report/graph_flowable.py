"""A reportlab Flowable that draws a bounded transaction-graph snapshot."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.platypus import Flowable

from app.schemas.graph import GraphNode, GraphResult

_ROOT = colors.HexColor(0x1F6FEB)
_VASP = colors.HexColor(0x8250DF)
_RISK = colors.HexColor(0xD1242F)
_PLAIN = colors.HexColor(0x57606A)
_LINE = colors.HexColor(0xAFB8C1)
_TEXT = colors.HexColor(0x1F2328)


def _short(addr: str) -> str:
    return f"{addr[:6]}…{addr[-4:]}" if len(addr) > 12 else addr


class GraphFlowable(Flowable):  # type: ignore[misc]
    """Layered (by hop depth) node/edge diagram scaled to the frame width."""

    def __init__(self, graph: GraphResult, height: float = 230, max_nodes: int = 22):
        super().__init__()
        self.graph = graph
        self.height = height
        self.max_nodes = max_nodes
        self.width = 0.0

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        self.width = avail_width
        return (avail_width, self.height)

    def draw(self) -> None:
        c = self.canv
        nodes = self.graph.nodes[: self.max_nodes]
        if not nodes:
            c.setFillColor(_PLAIN)
            c.setFont("Helvetica", 9)
            c.drawString(4, self.height - 14, "No outgoing activity within bounds.")
            return

        shown = {n.address for n in nodes}
        by_depth: dict[int, list[GraphNode]] = {}
        for n in nodes:
            by_depth.setdefault(n.depth, []).append(n)
        depths = sorted(by_depth)
        col_w = self.width / max(len(depths), 1)
        box_w = min(col_w - 12, 150)
        box_h = 26

        pos: dict[str, tuple[float, float]] = {}
        for di, d in enumerate(depths):
            col = by_depth[d]
            row_h = self.height / max(len(col), 1)
            for ri, n in enumerate(col):
                cx = di * col_w + col_w / 2
                cy = self.height - (ri * row_h + row_h / 2)
                pos[n.address] = (cx, cy)

        # Edges first.
        c.setStrokeColor(_LINE)
        c.setLineWidth(0.7)
        for e in self.graph.edges:
            if e.from_address in shown and e.to_address in shown:
                x1, y1 = pos[e.from_address]
                x2, y2 = pos[e.to_address]
                c.line(x1 + box_w / 2, y1, x2 - box_w / 2, y2)

        # Nodes.
        for n in nodes:
            cx, cy = pos[n.address]
            if n.depth == 0:
                stroke = _ROOT
            elif n.label_name and any(
                k in n.label_name.lower() for k in ("tornado", "mixer", "sanction")
            ):
                stroke = _RISK
            elif n.vasp_name:
                stroke = _VASP
            else:
                stroke = _PLAIN
            x = cx - box_w / 2
            y = cy - box_h / 2
            c.setStrokeColor(stroke)
            c.setFillColor(colors.white)
            c.setLineWidth(1.1)
            c.roundRect(x, y, box_w, box_h, 4, stroke=1, fill=1)
            c.setFillColor(_TEXT)
            c.setFont("Courier", 7.5)
            c.drawCentredString(cx, cy + 2, _short(n.address))
            label = n.vasp_name or n.label_name
            if label:
                c.setFillColor(stroke)
                c.setFont("Helvetica-Bold", 7)
                c.drawCentredString(cx, cy - 7, label[:22])

        if len(self.graph.nodes) > self.max_nodes:
            c.setFillColor(_PLAIN)
            c.setFont("Helvetica-Oblique", 7)
            c.drawString(
                2,
                2,
                f"+{len(self.graph.nodes) - self.max_nodes} more nodes not shown",
            )
