"""Build the editable, hand-drawn ITS Sukolilo schematic map."""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx


CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 700
CANVAS_PADDING = 60
GOAL_ID = "informatics"

# Source positions from the supplied ~1930 x 1950 hand-drawn image.
# Coordinates are scaled independently into the padded canvas without flipping.
NODES = [
    ("main_gate", 363, 810, "Main Gate"),
    ("graha", 520, 291, "Graha"),
    ("d3_pens", 969, 282, "D3 / PENS"),
    ("robotics", 1546, 296, "Robotics"),
    ("informatics", 1465, 632, "Informatics"),
    ("manarul_ilmi", 514, 1248, "Manarul Ilmi"),
    ("library", 978, 942, "Library"),
    ("canteen", 857, 1420, "Canteen"),
    ("biology", 737, 1707, "Biology"),
    ("chemical_eng", 1411, 1220, "Chemical Engineering"),
    ("electrical_eng", 1349, 1627, "Electrical Engineering"),
]

# Undirected edges; costs are walking-distance weights in meters, not hops.
EDGES = [
    ("main_gate", "graha", 550),
    ("main_gate", "manarul_ilmi", 450),
    ("graha", "d3_pens", 280),
    ("d3_pens", "robotics", 550),
    ("d3_pens", "informatics", 750),
    ("robotics", "informatics", 300),
    ("informatics", "library", 350),
    ("informatics", "chemical_eng", 500),
    ("informatics", "electrical_eng", 1400),
    ("library", "manarul_ilmi", 350),
    ("library", "canteen", 400),
    ("library", "chemical_eng", 200),
    ("manarul_ilmi", "canteen", 300),
    # TODO: Placeholder edge; this link is unlabeled in the source drawing.
    ("manarul_ilmi", "biology", 500),
    ("canteen", "biology", 260),
    ("canteen", "electrical_eng", 650),
    ("chemical_eng", "electrical_eng", 300),
    # TODO: Placeholder edge; this link is unlabeled in the source drawing.
    ("biology", "electrical_eng", 600),
]

NODE_COLORS = [
    "#482878",
    "#3e4989",
    "#31688e",
    "#26828e",
    "#1f9e89",
    "#35b779",
    "#6ece58",
    "#b5de2b",
    "#fde725",
]


def scale_nodes(nodes):
    """Scale drawing-image coordinates to the padded canvas without inversion."""
    x_values = [x for _, x, _, _ in nodes]
    y_values = [y for _, _, y, _ in nodes]
    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)
    usable_width = CANVAS_WIDTH - 2 * CANVAS_PADDING
    usable_height = CANVAS_HEIGHT - 2 * CANVAS_PADDING

    result = []
    for node_id, source_x, source_y, _ in nodes:
        x = CANVAS_PADDING + (source_x - min_x) / (max_x - min_x) * usable_width
        y = CANVAS_PADDING + (source_y - min_y) / (max_y - min_y) * usable_height
        result.append({"id": node_id, "x": round(x), "y": round(y)})
    return result


def build_map():
    """Build the exact JSON schema using only the editable lists above."""
    return {
        "nodes": scale_nodes(NODES),
        "edges": [
            {"from": source, "to": target, "cost": cost}
            for source, target, cost in EDGES
        ],
        "goal": GOAL_ID,
    }


def validate_map(map_data):
    """Print the requested structural checks and return whether all passed."""
    node_ids = [node["id"] for node in map_data["nodes"]]
    node_id_set = set(node_ids)
    canonical_edges = [
        frozenset((edge["from"], edge["to"]))
        for edge in map_data["edges"]
    ]
    endpoints_exist = all(
        edge["from"] in node_id_set and edge["to"] in node_id_set
        for edge in map_data["edges"]
    )
    no_duplicate_edges = (
        len(canonical_edges) == len(set(canonical_edges))
        and all(len(edge) == 2 for edge in canonical_edges)
    )
    positive_integer_costs = all(
        isinstance(edge["cost"], int)
        and not isinstance(edge["cost"], bool)
        and edge["cost"] > 0
        for edge in map_data["edges"]
    )

    graph = nx.Graph()
    graph.add_nodes_from(node_ids)
    graph.add_edges_from(
        (edge["from"], edge["to"])
        for edge in map_data["edges"]
        if edge["from"] in node_id_set and edge["to"] in node_id_set
    )
    connected = bool(node_ids) and nx.is_connected(graph)
    goal_reachable = (
        map_data.get("goal") in graph
        and len(nx.node_connected_component(graph, map_data["goal"])) == len(node_ids)
    )

    checks = [
        ("graph is connected", connected),
        ("informatics is reachable from every node", goal_reachable),
        ("no duplicate edges", no_duplicate_edges),
        ("every edge endpoint exists as a node", endpoints_exist),
        ("all costs are positive integers", positive_integer_costs),
    ]
    for description, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'} | {description}")
    return all(passed for _, passed in checks)


def audit_map(map_data):
    """Print node degrees, goal-hop distances, and graph-wide hop metrics."""
    graph = nx.Graph()
    graph.add_nodes_from(node["id"] for node in map_data["nodes"])
    graph.add_edges_from((edge["from"], edge["to"]) for edge in map_data["edges"])
    degrees = dict(graph.degree())
    hops = (
        nx.single_source_shortest_path_length(graph, map_data["goal"])
        if map_data["goal"] in graph
        else {}
    )
    average_degree = sum(degrees.values()) / len(degrees) if degrees else 0
    longest_path = max(hops.values(), default=0)
    cycles = graph.number_of_edges() - graph.number_of_nodes() + 1

    print("NODE | DEGREE | HOPS_TO_INFORMATICS")
    for node in map_data["nodes"]:
        node_id = node["id"]
        distance = hops.get(node_id, "UNREACHABLE")
        print(f"{node_id} | {degrees[node_id]} | {distance}")
    print(f"AVERAGE_DEGREE | {average_degree:.3f}")
    print(f"LONGEST_SHORTEST_PATH_HOPS | {longest_path}")
    print(f"INDEPENDENT_CYCLES | {cycles}")
    return graph, hops


def boxes_overlap(first, second, padding=2):
    return (
        first.x0 < second.x1 + padding
        and first.x1 + padding > second.x0
        and first.y0 < second.y1 + padding
        and first.y1 + padding > second.y0
    )


def box_hits_other_node(box, node_centers, own_node, radius=14):
    for node_id, (center_x, center_y) in node_centers.items():
        if node_id == own_node:
            continue
        closest_x = min(max(center_x, box.x0), box.x1)
        closest_y = min(max(center_y, box.y0), box.y1)
        if math.hypot(center_x - closest_x, center_y - closest_y) < radius:
            return True
    return False


def place_node_labels(axis, positions, labels, node_centers, renderer):
    offsets = [
        (0, 17),
        (0, -19),
        (27, 0),
        (-27, 0),
        (32, 18),
        (-32, 18),
        (32, -18),
        (-32, -18),
        (0, 29),
        (0, -31),
        (48, 0),
        (-48, 0),
        (50, 20),
        (-50, 20),
    ]
    placed_boxes = []
    texts = []
    ordered_ids = [GOAL_ID] + [
        node_id for node_id in labels if node_id != GOAL_ID
    ]

    for node_id in ordered_ids:
        x, y = positions[node_id]
        placed = False
        for offset in offsets:
            text = axis.annotate(
                labels[node_id],
                (x, y),
                xytext=offset,
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold" if node_id == GOAL_ID else "regular",
                color="#17242b",
                bbox={
                    "facecolor": "#ffffff",
                    "edgecolor": "none",
                    "alpha": 0.9,
                    "boxstyle": "round,pad=0.15",
                },
                zorder=5,
            )
            box = text.get_window_extent(renderer=renderer)
            if (
                not box_hits_other_node(box, node_centers, node_id)
                and not any(boxes_overlap(box, previous) for previous in placed_boxes)
            ):
                texts.append(text)
                placed_boxes.append(box)
                placed = True
                break
            text.remove()
        if not placed:
            raise ValueError(f"Could not place non-overlapping label for {node_id}")
    return texts, placed_boxes


def place_edge_labels(axis, graph, positions, node_centers, blocked_boxes, renderer):
    offsets = [0, 12, -12, 22, -22, 32, -32, 44, -44]
    placed_boxes = list(blocked_boxes)
    texts = []
    skipped = []

    for source, target, data in graph.edges(data=True):
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            skipped.append((source, target))
            continue
        normal_x, normal_y = -dy / length, dx / length
        midpoint = ((x1 + x2) / 2, (y1 + y2) / 2)
        placed = False

        for offset in offsets:
            text = axis.annotate(
                str(data["cost"]),
                midpoint,
                xytext=(normal_x * offset, normal_y * offset),
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=6,
                color="#263840",
                bbox={
                    "facecolor": "#ffffff",
                    "edgecolor": "none",
                    "alpha": 0.88,
                    "boxstyle": "round,pad=0.1",
                },
                zorder=4,
            )
            box = text.get_window_extent(renderer=renderer)
            if (
                not box_hits_other_node(box, node_centers, None, radius=12)
                and not any(boxes_overlap(box, previous) for previous in placed_boxes)
            ):
                texts.append(text)
                placed_boxes.append(box)
                placed = True
                break
            text.remove()
        if not placed:
            skipped.append((source, target))
    return texts, skipped


def save_preview(map_data, output_path):
    """Save a readable map preview with collision-checked labels."""
    graph = nx.Graph()
    positions = {
        node["id"]: (node["x"], node["y"])
        for node in map_data["nodes"]
    }
    labels = {
        node_id: display_name
        for node_id, _, _, display_name in NODES
    }
    graph.add_nodes_from(positions)
    graph.add_edges_from(
        (edge["from"], edge["to"], {"cost": edge["cost"]})
        for edge in map_data["edges"]
    )
    hops = nx.single_source_shortest_path_length(graph, map_data["goal"])
    maximum_hops = max(hops.values(), default=1)
    node_colors = [NODE_COLORS[min(hops[node_id], len(NODE_COLORS) - 1)]
                   for node_id in graph.nodes]

    figure, axis = plt.subplots(figsize=(12, 8), dpi=120, facecolor="#f4f6f2")
    axis.set_facecolor("#f4f6f2")
    nx.draw_networkx_edges(
        graph,
        positions,
        ax=axis,
        edge_color="#81958e",
        width=2,
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        ax=axis,
        node_color=node_colors,
        edgecolors="#ffffff",
        linewidths=2,
        node_size=330,
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=[map_data["goal"]],
        ax=axis,
        node_color=[NODE_COLORS[0]],
        edgecolors="#f2bd45",
        linewidths=5,
        node_size=520,
    )
    axis.set_xlim(0, CANVAS_WIDTH)
    axis.set_ylim(CANVAS_HEIGHT, 0)
    axis.set_aspect("equal", adjustable="box")
    axis.axis("off")
    figure.tight_layout()
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    node_centers = {
        node_id: axis.transData.transform(position)
        for node_id, position in positions.items()
    }

    _, node_label_boxes = place_node_labels(
        axis, positions, labels, node_centers, renderer
    )
    _, skipped_edges = place_edge_labels(
        axis, graph, positions, node_centers, node_label_boxes, renderer
    )
    figure.canvas.draw()
    figure.savefig(output_path, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)

    print(f"PREVIEW | {output_path}")
    print(f"EDGE_LABELS_SKIPPED_TO_AVOID_OVERLAP | {len(skipped_edges)}")
    for source, target in skipped_edges:
        print(f"  {source} <-> {target}")
    print(f"NODE_COLORS | hop distance range 0-{maximum_hops}; goal highlighted")


def main():
    map_data = build_map()
    valid = validate_map(map_data)
    audit_map(map_data)

    maps_dir = Path(__file__).resolve().parent
    output_path = maps_dir / "its_sukolilo.json"
    backup_path = maps_dir / "its_sukolilo_v1.json"
    preview_path = maps_dir / "preview.png"
    if output_path.exists() and not backup_path.exists():
        backup_path.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"BACKUP | {backup_path}")
    output_path.write_text(
        json.dumps(map_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"MAP_JSON | {output_path}")
    save_preview(map_data, preview_path)
    if not valid:
        raise ValueError("Map validation failed; see FAIL checks above")


if __name__ == "__main__":
    main()
