from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


NodeKind = Literal["start", "command", "upload"]


@dataclass(frozen=True)
class FlowNode:
    id: str
    kind: NodeKind
    label: str
    x: int
    y: int
    text: str = ""
    local_path: str = ""
    remote_path: str = ""


@dataclass(frozen=True)
class FlowEdge:
    source_id: str
    target_id: str


@dataclass(frozen=True)
class OperationFlow:
    nodes: list[FlowNode]
    edges: list[FlowEdge]

    def to_operations_text(self) -> str:
        lines: list[str] = []
        for node in self.ordered_operation_nodes():
            if node.kind == "command":
                command = node.text.strip()
                if not command:
                    raise ValueError(f'Command node "{node.label}" is empty')
                lines.append(command)
            elif node.kind == "upload":
                if not node.local_path.strip() or not node.remote_path.strip():
                    raise ValueError(f'Upload node "{node.label}" must include local and remote paths')
                lines.append(f"upload {_quote_path(node.local_path)} {_quote_path(node.remote_path)}")

        return "\n".join(lines) + ("\n" if lines else "")

    def ordered_operation_nodes(self) -> list[FlowNode]:
        nodes_by_id = {node.id: node for node in self.nodes}
        start_nodes = [node for node in self.nodes if node.kind == "start"]
        if len(start_nodes) != 1:
            raise ValueError("Flow must contain exactly one start node")

        outgoing: dict[str, list[str]] = {}
        incoming_count: dict[str, int] = {node.id: 0 for node in self.nodes}
        for edge in self.edges:
            if edge.source_id not in nodes_by_id or edge.target_id not in nodes_by_id:
                raise ValueError("Flow contains an arrow linked to a missing node")
            outgoing.setdefault(edge.source_id, []).append(edge.target_id)
            incoming_count[edge.target_id] += 1

        for node_id, targets in outgoing.items():
            if len(targets) > 1:
                label = nodes_by_id[node_id].label
                raise ValueError(f'Node "{label}" can have only one outgoing arrow')
        for node in self.nodes:
            if node.kind != "start" and incoming_count[node.id] > 1:
                raise ValueError(f'Node "{node.label}" can have only one incoming arrow')

        ordered: list[FlowNode] = []
        visited: set[str] = set()
        current_id = start_nodes[0].id
        while True:
            if current_id in visited:
                raise ValueError("Flow contains a cycle")
            visited.add(current_id)

            targets = outgoing.get(current_id, [])
            if not targets:
                break
            current_id = targets[0]
            current_node = nodes_by_id[current_id]
            if current_node.kind == "start":
                raise ValueError("Start node cannot appear after another node")
            ordered.append(current_node)

        connected = visited | {node.id for node in ordered}
        disconnected = [node.label for node in self.nodes if node.id not in connected]
        if disconnected:
            raise ValueError(f"Flow contains disconnected node(s): {', '.join(disconnected)}")

        return ordered

    def save(self, path: Path) -> None:
        data = {
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "OperationFlow":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            nodes=[FlowNode(**node) for node in data.get("nodes", [])],
            edges=[FlowEdge(**edge) for edge in data.get("edges", [])],
        )


def _quote_path(path: str) -> str:
    stripped = path.strip()
    if any(char.isspace() for char in stripped):
        escaped = stripped.replace('"', '\\"')
        return f'"{escaped}"'
    return stripped
