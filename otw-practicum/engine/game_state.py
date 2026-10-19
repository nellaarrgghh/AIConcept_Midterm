"""
Campus Pursuit game engine (NEL).

This file is the single source of truth for the rules. The web page and the
agents never re-implement them; they only call the methods below.

Rules:
  * Two pieces on an undirected graph: the Student (human) and the Proctor (AI).
  * Alternating turns, the Student moves first. A move is a node id: a
    neighbor of the current node. The Student may also wait (move to its own
    node); the Proctor may NOT wait (it only waits if it has no neighbor at
    all, so the game never gets stuck).
  * Proctor wins if both pieces share a node (no matter who moved onto whom).
  * Student wins on reaching the goal node (map_data["goal"]).
  * `turn` counts completed rounds and increases after the Proctor moves.
    When turn reaches turn_limit, the Proctor wins. So a Student who reaches
    the goal on the last round still wins.
  * The player may not start on the goal or fewer than `min_hops` edges from
    it (the server sets min_hops = MIN_START_HOPS = 2).
"""

import heapq
import json
import math
import random
from collections import deque

STUDENT = "student"
PROCTOR = "proctor"

# Default minimum hop distance (edges) between the player's start and the goal.
# The server defines its own MIN_START_HOPS constant and passes it explicitly.
DEFAULT_MIN_START_HOPS = 2


# Map helpers

def load_map(path):
    """Read a map JSON file and return it as a dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_map(map_data):
    """
    Validate map structure:
      - goal is in nodes
      - every edge endpoint exists as a node
      - no duplicate edges (undirected)
      - graph is connected
      - goal is reachable from every node
    Raises ValueError with a clear message if validation fails.
    """
    if "nodes" not in map_data or "edges" not in map_data or "goal" not in map_data:
        raise ValueError("Map missing required fields ('nodes', 'edges', 'goal')")

    node_ids = set()
    for node in map_data["nodes"]:
        if "id" not in node:
            raise ValueError("Node is missing 'id'")
        nid = node["id"]
        if nid in node_ids:
            raise ValueError("Duplicate node id %r in map" % nid)
        node_ids.add(nid)

    goal = map_data["goal"]
    if goal not in node_ids:
        raise ValueError("Goal node %r is not in the map nodes" % goal)

    seen_edges = set()
    for edge in map_data["edges"]:
        if "from" not in edge or "to" not in edge or "cost" not in edge:
            raise ValueError("Edge missing 'from', 'to', or 'cost': %r" % (edge,))
        u, v = edge["from"], edge["to"]
        if u not in node_ids:
            raise ValueError("Edge endpoint %r does not exist as a node" % u)
        if v not in node_ids:
            raise ValueError("Edge endpoint %r does not exist as a node" % v)
        if u == v:
            raise ValueError("Self-loop edge on node %r is not allowed" % u)
        canonical = (u, v) if u < v else (v, u)
        if canonical in seen_edges:
            raise ValueError("Duplicate edge between %r and %r" % (u, v))
        seen_edges.add(canonical)

    adj = build_adjacency(map_data)
    # Check connectivity and goal reachability
    dist_from_goal = hop_distances(adj, goal)
    if len(dist_from_goal) != len(node_ids):
        unreached = node_ids - set(dist_from_goal.keys())
        raise ValueError("Graph is not connected; goal %r is not reachable from: %s"
                         % (goal, ", ".join(unreached)))
    return adj


def build_adjacency(map_data):
    """
    Turn the map's edge list into an adjacency dict:
        {node_id: {neighbor_id: cost, ...}, ...}
    Edges are undirected, so each edge is added in both directions.
    Neighbor order follows the order of edges in the file, so results are
    deterministic (important for comparing Minimax and Alpha-Beta).
    """
    adj = {node["id"]: {} for node in map_data["nodes"]}
    for edge in map_data["edges"]:
        a, b, cost = edge["from"], edge["to"], edge["cost"]
        if a not in adj or b not in adj:
            raise ValueError("Edge %s-%s uses an unknown node" % (a, b))
        adj[a][b] = cost
        adj[b][a] = cost
    if map_data["goal"] not in adj:
        raise ValueError("Goal node %r is not in the map" % map_data["goal"])
    return adj


def hop_distances(adj, source):
    """Breadth-first search: number of edges from `source` to every reachable node."""
    dist = {source: 0}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for nb in adj[node]:
            if nb not in dist:
                dist[nb] = dist[node] + 1
                queue.append(nb)
    return dist


def default_turn_limit(adj):
    """
    Turn limit T = ceil(1.5 * longest shortest path), measured in hops
    (edges), because a turn moves one edge regardless of its length in meters.
    """
    diameter = 0
    for node in adj:
        dist = hop_distances(adj, node)
        if len(dist) != len(adj):
            raise ValueError("Map is not connected (checked from %r)" % node)
        diameter = max(diameter, max(dist.values()))
    return math.ceil(1.5 * diameter)


def shortest_distances(adj, source):
    """Dijkstra: shortest walking distance in meters from `source` to every node."""
    dist = {source: 0}
    heap = [(0, source)]
    while heap:
        d, node = heapq.heappop(heap)
        if d > dist[node]:
            continue  # stale heap entry
        for nb, cost in adj[node].items():
            nd = d + cost
            if nd < dist.get(nb, math.inf):
                dist[nb] = nd
                heapq.heappush(heap, (nd, nb))
    return dist


def allowed_player_starts(map_data, min_hops=DEFAULT_MIN_START_HOPS):
    """Node ids the player may start on: at least `min_hops` edges from the goal (never the goal)."""
    adj = build_adjacency(map_data)
    hops = hop_distances(adj, map_data["goal"])  # undirected, so goal->node == node->goal
    return [node["id"] for node in map_data["nodes"]
            if node["id"] != map_data["goal"] and hops.get(node["id"], math.inf) >= min_hops]


def validate_player_start(map_data, player_start, min_hops=0):
    """
    Raise ValueError if the player's chosen start is unknown, the goal, or
    (when min_hops > 0) fewer than `min_hops` edges from the goal.
    """
    node_ids = [node["id"] for node in map_data["nodes"]]
    if player_start not in node_ids:
        raise ValueError("Unknown player start %r" % player_start)
    if player_start == map_data["goal"]:
        raise ValueError("Player start %r cannot be the goal" % player_start)
    if min_hops > 0:
        allowed = allowed_player_starts(map_data, min_hops)
        if player_start not in allowed:
            hops = hop_distances(build_adjacency(map_data), map_data["goal"])[player_start]
            raise ValueError(
                "Player start %r is only %d hop(s) from the goal %r; it must be at least %d. "
                "Allowed starts: %s" % (player_start, hops, map_data["goal"], min_hops, ", ".join(allowed)))


def pick_ai_start(map_data, player_start, seed=None, min_hops=0):
    """
    Check the player's start (see validate_player_start), then pick the
    Proctor's random start node: any node except the player's start and the
    goal. A fixed `seed` always gives the same answer.
    """
    validate_player_start(map_data, player_start, min_hops=min_hops)
    node_ids = [node["id"] for node in map_data["nodes"]]
    candidates = [n for n in node_ids if n != player_start and n != map_data["goal"]]
    if not candidates:
        raise ValueError("Map has no valid start node for the AI")
    rng = random.Random(seed)  # local generator: never touches global random state
    return rng.choice(candidates)



# GameState
class GameState:
    """
    One position in the game. Treat it as immutable: apply() returns a NEW
    state and never changes this one.

    Fields: turn, student, proctor, to_move ('student' or 'proctor'),
    turn_limit, plus adj (adjacency dict) and goal. `adj` is shared between
    all states of a game and must never be modified.
    """

    # slots keeps each state small, which helps when agents create
    # thousands of states during a search.
    slots = ("adj", "goal", "student", "proctor", "to_move", "turn", "turn_limit")

    def __init__(self, adj, goal, student, proctor, to_move=STUDENT, turn=0, turn_limit=None):
        self.adj = adj
        self.goal = goal
        self.student = student
        self.proctor = proctor
        self.to_move = to_move
        self.turn = turn
        self.turn_limit = turn_limit if turn_limit is not None else default_turn_limit(adj)

    @classmethod
    def from_map(cls, map_data, student, proctor, turn_limit=None):
        """Create the starting state of a new game from a map dict."""
        adj = build_adjacency(map_data)
        for name, node in (("student", student), ("proctor", proctor)):
            if node not in adj:
                raise ValueError("Unknown %s start %r" % (name, node))
        return cls(adj, map_data["goal"], student, proctor, STUDENT, 0, turn_limit)

    # -- rules 

    def legal_moves(self):
        """
        Node ids the side to move may go to.
          Student: waiting (current node) first, then neighbors.
          Proctor: neighbors only (no waiting). If the Proctor has no neighbor
          at all, it is allowed to stay put so the game can continue.
        """
        if self.is_terminal():
            return []
        if self.to_move == STUDENT:
            return [self.student] + list(self.adj[self.student])
        neighbors = list(self.adj[self.proctor])
        return neighbors if neighbors else [self.proctor]

    def apply(self, move):
        """Return a new state after the side to move goes to `move`."""
        if move not in self.legal_moves():
            raise ValueError("Illegal move %r for %s" % (move, self.to_move))
        new = self.copy()
        if self.to_move == STUDENT:
            new.student = move
            new.to_move = PROCTOR
        else:
            new.proctor = move
            new.to_move = STUDENT
            new.turn += 1  # a round is complete after the Proctor moves
        return new

    def copy(self):
        """Cheap copy: only the small fields are copied, `adj` is shared."""
        return GameState(self.adj, self.goal, self.student, self.proctor,
                         self.to_move, self.turn, self.turn_limit)

    def winner(self):
        """'student', 'proctor', or None if the game is still going."""
        if self.student == self.proctor:  # catch is checked first (covers walking into the Proctor)
            return PROCTOR
        if self.student == self.goal:
            return STUDENT
        if self.turn >= self.turn_limit:
            return PROCTOR
        return None

    def is_terminal(self):
        return self.winner() is not None

    def utility(self, player):
        """+1 if `player` has won, -1 if they have lost, 0 while the game is ongoing."""
        w = self.winner()
        if w is None:
            return 0
        return 1 if w == player else -1

    def repr(self):
        return ("GameState(turn=%d/%d, student=%r, proctor=%r, to_move=%r)"
                % (self.turn, self.turn_limit, self.student, self.proctor, self.to_move))
