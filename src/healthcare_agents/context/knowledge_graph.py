"""Knowledge graph for member, provider, plan, policy, and claims relationships (Layer 4)."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relationship: str


class KnowledgeGraph:
    """In-memory knowledge graph stub for dev/test.

    Production deployments connect to Neo4j, Amazon Neptune, or similar.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._seed_demo_data()

    def _seed_demo_data(self) -> None:
        self.add_node("member-001", "member", {"name": "Demo Member", "plan": "Medicaid Plus"})
        self.add_node(
            "provider-101",
            "provider",
            {"name": "City Medical Group", "npi": "1234567890"},
        )
        self.add_node("plan-medicaid", "plan", {"name": "Medicaid Plus", "state": "NY"})
        self.add_edge("member-001", "plan-medicaid", "enrolled_in")
        self.add_edge("member-001", "provider-101", "assigned_pcp")

    def add_node(
        self,
        node_id: str,
        node_type: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphNode:
        node = GraphNode(node_id=node_id, node_type=node_type, properties=properties or {})
        self._nodes[node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str, relationship: str) -> GraphEdge:
        edge = GraphEdge(source_id=source_id, target_id=target_id, relationship=relationship)
        self._edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def neighbors(self, node_id: str, relationship: str | None = None) -> list[GraphNode]:
        neighbor_ids = [
            e.target_id
            for e in self._edges
            if e.source_id == node_id and (relationship is None or e.relationship == relationship)
        ]
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def query_context(self, member_id: str) -> dict[str, Any]:
        member = self.get_node(member_id)
        if not member:
            return {}

        return {
            "member": member.properties,
            "plan": [n.properties for n in self.neighbors(member_id, "enrolled_in")],
            "providers": [n.properties for n in self.neighbors(member_id, "assigned_pcp")],
        }
