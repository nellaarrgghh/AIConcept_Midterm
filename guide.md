# OTW Practicum: Project Guide (Final Concept)

A Human vs. AI chase game on the ITS Sukolilo map. The human is a Student racing to the Informatics Department, and an AI Proctor/TA tries to catch them. Three algorithms set the difficulty: UCS (easy), Minimax (medium), and Alpha-Beta (hard).

## 1. Concept

| Item | Decision |
| --- | --- |
| Game | Turn-based chase on a graph of ITS Sukolilo locations |
| Human role | Student: reach the Department of Informatics |
| AI role | Proctor/TA: catch the Student |
| Map | ITS Sukolilo only |
| Starting positions | The player chooses their start node (at least 2 hops from the goal). The AI starts on a random node (not the player's node and not Informatics) |
| Difficulty | Easy: UCS. Medium: Minimax (depth 3). Hard: Alpha-Beta (iterative deepening, 1s budget, capped at remaining plies) |
| Moves | Alternating turns, the player first. Each turn: Student moves along one edge or waits. Proctor must move to an adjacent neighbor (cannot wait) |
| Student wins | Reaches Informatics before the turn limit |
| Proctor wins | Lands on the Student's node, Student steps onto Proctor, or the turn limit ($T = 6$) runs out |
| Edge cost | Real walking distance in meters, from OpenStreetMap |

Nothing else is in the game: no rain, no shade, no partial information.

**Why it fits the assignment:** three algorithms from class are implemented and compared in one game, the topic is campus life, and the game can be demoed live.

## 2. The three algorithms

| Level | Algorithm | How the Proctor plays |
| --- | --- | --- |
| Easy | UCS | Each turn, finds the cheapest meter path to the Student's current node and takes the first step. It never predicts the Student's reply, so detours beat it |
| Medium | Minimax | Depth-limited game tree (fixed depth 3). Considers the Student's replies, but misses longer traps |
| Hard | Alpha-Beta | Same decisions as Minimax, with pruning, plus iterative deepening (1-second time limit, capped at remaining plies until turn limit $T = 6$) |

**Evaluation function** (used by Minimax and Alpha-Beta), from the Student's view: hop_distance(Proctor, Student) minus hop_distance(Student, Informatics). The Student maximizes it and the Proctor minimizes it. Distances come from an all-pairs BFS hop table on the map, computed once and cached. Win/loss terminal scores are depth-dependent (a faster catch is rewarded), and root ties prefer moving closer to the Student.

**Key point for the report:** Minimax and Alpha-Beta choose identical moves at the same depth. Alpha-Beta is stronger only because pruning lets it search deeper in the same time. Compare them on nodes expanded, time per move, and depth reached.

## 3. Architecture

The Python engine is the single source of truth for the rules. The web page only draws the state and sends the human's moves.

```
Browser (HTML/JS)  <-- JSON -->  Flask API  -->  Python GameState + Agents
                                                    |
                                  Tournament runner --> CSV logs
```

### Map file (maps/its\_sukolilo.json)

| Field | Meaning |
| --- | --- |
| nodes | List of id, x, y (pixel position for the canvas) |
| edges | List of from, to, cost (meters) |
| goal | Node id of the Informatics Department, for example informatics |

The start nodes are not in the file. The player picks theirs and the server picks the AI's.

### API

| Endpoint | Purpose |
| --- | --- |
| GET /map | Returns the map file, plus `turn_limit` (6), `allowed_starts`, and `min_start_hops` (2) |
| POST /new\_game | Takes difficulty and player\_start ($\ge 2$ hops from goal). Picks a random AI start. Returns the initial state with `turn_limit` and `allowed_starts` |
| POST /move | Takes state and the human's move. Applies it, the AI replies, returns the new state and ai\_move |

**State:** turn, student, proctor, to\_move, winner, turn_limit. The server is stateless, so the browser sends the state back with each move.

**Agent interface:** every agent has choose\_move(state) and returns a node id.

## 4. Map dataset from OpenStreetMap (OSM)

Download the walking network around ITS Sukolilo with OSMnx, then keep 15 to 25 key locations.

1. Install: `pip install osmnx networkx matplotlib`.
2. In Google Maps, right-click the middle of the campus and copy the lat/lon.
3. Download and plot the walking graph. It will show far more nodes than the game needs.
4. Choose 15 to 25 locations: gates, library, rectorate, main departments, canteens, and the Informatics Department. Copy each lat/lon from Google Maps.
5. Snap each location to its nearest OSM node and connect nearby locations by walking distance (script below).
6. Fix gaps by hand, since OSM campus paths are often incomplete. Compare with satellite view, then add or remove edges.
7. Convert lat/lon to canvas x/y by linear scaling (flip y).
8. Export to the map JSON, then plot it. Check that the graph is connected and Informatics is reachable from every node.

```
import osmnx as ox, networkx as nx, json
center = (LAT, LON)  # campus center from Google Maps
G = ox.graph_from_point(center, dist=1200, network_type='walk')
places = {'gate_main': (LAT, LON), 'library': (LAT, LON), 'informatics': (LAT, LON)}
nodes = {n: ox.distance.nearest_nodes(G, lon, lat) for n, (lat, lon) in places.items()}
names = list(nodes)
edges = []
for i, a in enumerate(names):
    for b in names[i+1:]:
        d = nx.shortest_path_length(G, nodes[a], nodes[b], weight='length')
        if d < 400:  # connect only locations within 400 m
            edges.append({'from': a, 'to': b, 'cost': round(d)})

lats = [p[0] for p in places.values()]
lons = [p[1] for p in places.values()]
def to_xy(lat, lon, W=1000, H=700):
    x = (lon - min(lons)) / (max(lons) - min(lons)) * W
    y = (1 - (lat - min(lats)) / (max(lats) - min(lats))) * H
    return round(x), round(y)

out = {'nodes': [{'id': n, 'x': to_xy(*places[n])[0], 'y': to_xy(*places[n])[1]} for n in places],
       'edges': edges, 'goal': 'informatics'}
json.dump(out, open('maps/its_sukolilo.json', 'w'), indent=2)
```

Credit OpenStreetMap contributors (ODbL license) in the references.

## 5. Task division

| Division | Member | Owns |
| --- | --- | --- |
| Algo (BE) | BE-1: Engine lead | GameState, Flask API, repo and integration, Random agent |
| Algo (BE) | BE-2: Agents | UCS, Minimax, Alpha-Beta, evaluation function, tournament runner, plots |
| Game (FE) | FE-1: Map and visuals | OSM map dataset, map rendering, piece animation |
| Game (FE) | FE-2: Interaction and presentation | Game page, start-node selection, difficulty menu, hosting, slides |

**Report ownership**

| Part | Writer |
| --- | --- |
| Cover page, Chapter 1 (background, problem, benefits) | FE-1 and FE-2 |
| Chapter 2 (rules, algorithms, architecture) | BE-1 and BE-2 |
| Chapter 3 (experiments and discussion, GitHub link) | BE-2, with BE-1 on the setup |
| Chapter 4 (conclusion), references | Everyone |

## 6. Step-by-step per person

### BE-1: Engine lead (Mac)

1. **Day 1:** open Terminal and check `python3 --version` and `git --version`. Accept the macOS prompt to install the command line tools if it appears.
2. **Day 1:** create the project folders and files (section 8), then run `python3 -m venv .venv`, `source .venv/bin/activate`, and `pip install flask flask-cors pandas matplotlib networkx`.
3. **Day 1:** create the GitHub repo, push, and add the other three as collaborators.
4. **Day 1:** write GameState with fields turn, student, proctor, to\_move, and turn\_limit, and methods legal\_moves(), apply(move), copy(), winner(), is\_terminal(), and utility(player).
5. **Day 1:** add a function that picks the AI's random start: any node except the player's start and Informatics, using a seeded random generator.
6. **Day 1:** write the Random agent and a script that plays Random vs. Random 100 times on a small test map. Neither side should win every game.
7. **Day 1 evening:** push, then write the method names and move format in docs/interface.md so BE-2 can code against it.
8. **Day 2 AM:** write Flask with GET /map, POST /new\_game, and POST /move. Map difficulty to agents (easy is UCS, medium is Minimax depth 3, hard is Alpha-Beta with a 1-second limit). Enable CORS and test with curl.
9. **Day 2 PM:** choose the turn limit T (for example, the longest shortest path in the map times 1.5), so neither side always wins. Export 2 or 3 game logs as JSON.
10. **Day 3:** write the rules and architecture parts of Chapter 2, finish the README with run instructions, and test a fresh clone.

### BE-2: Agents

1. **Day 1:** write the evaluation function and a cached all-pairs shortest BFS hop-distance table.
2. **Day 1:** write Minimax with a depth limit and a node counter. The Student maximizes and the Proctor minimizes.
3. **Day 2 AM:** write Alpha-Beta by adding the cutoffs. Test that it returns the same move as Minimax on 100 random states at the same depth.
4. **Day 2 AM:** write the UCS agent: UCS to the Student's node, then take the first step.
5. **Day 2 AM:** add iterative deepening with a time limit to Alpha-Beta for the Hard level.
6. **Day 2 PM:** write a simulated Student for experiments (Greedy: always takes the shortest path to Informatics, and Random). Write the tournament runner: random start pairs, 100 or more games per Proctor agent, logging one CSV row per game (agent, student type, starts, winner, turns, nodes expanded, time per move).
7. **Day 2 evening:** make plots with pandas and matplotlib, then confirm that Hard beats Medium and Medium beats Easy.
8. **Day 3:** write the algorithm methods in Chapter 2 and all of Chapter 3.

### FE-1: Map and visuals

1. **Day 1, first 3 hours:** follow section 4 and send BE-1 a first map JSON, even with 8 nodes. Agree on the node id informatics.
2. **Day 1:** refine the map to 15 to 25 nodes. Check that it is connected.
3. **Day 1:** render the map on a canvas: edges as lines, nodes as circles, labels on key places, and Informatics highlighted.
4. **Day 1 PM:** draw the Student (blue) and Proctor (red) pieces and animate a move between two nodes.
5. **Day 2:** highlight the legal moves (neighbors of the player's node) on the player's turn.
6. **Day 2 PM:** polish colors, labels, and a legend. Add a start-node picker highlight so players see where they can start.
7. **Day 3:** take screenshots for the report and slides, and write the dataset section of Chapter 1.

### FE-2: Interaction and presentation

1. **Day 1:** build the page layout: a top bar (difficulty menu, New Game), the canvas, a HUD (turn, message), and a move log.
2. **Day 1:** create a mock API response file and a fetch wrapper with one BASE\_URL setting.
3. **Day 2 AM:** build the start flow: the player clicks a node to choose their start, then the page calls POST /new\_game and shows the AI's random start.
4. **Day 2 AM:** wire clicks on legal nodes to POST /move. Disable input while the AI is thinking.
5. **Day 2 AM:** add win and lose screens and a restart button.
6. **Day 2 PM:** host the static page on GitHub Pages, run Flask on a laptop, and test the full flow on the presentation laptop. Record one short screen video as a demo fallback.
7. **Day 3:** draft the slides, collect references, write Chapter 1 with FE-1, and time one full rehearsal at 15 minutes.

## 7. Three-day timeline

| Day | Algo division | Game division |
| --- | --- | --- |
| Day 1 AM | Together: freeze rules and the contract. BE-1 sets up the repo | FE-1 starts the OSM map. FE-2 starts the page on mock data |
| Day 1 PM | Engine plus Random vs. Random works. BE-2 starts evaluation and Minimax | Map v1 renders with moving pieces |
| Day 2 AM | Alpha-Beta and UCS done. Flask API live | Real API connected. Human vs. Easy works end to end |
| Day 2 PM | Tournament runs, plots, and difficulty check | Polish, hosting, demo video |
| Day 3 AM | Chapters 2 and 3 | Chapter 1, slides, references |
| Day 3 PM | Together: merge the report, final slides, rehearsal, and a check that the GitHub link opens |  |

## 8. Tools and repo structure

| Purpose | Tool |
| --- | --- |
| Engine, agents, experiments | Python 3 |
| API | Flask and flask-cors |
| Data and plots | pandas, matplotlib |
| Map data | OpenStreetMap through OSMnx, with Google Maps for coordinates |
| Game page | Plain HTML, CSS, and JavaScript with a canvas (no framework) |
| Hosting | GitHub Pages for the page, Flask on a laptop for live play |
| Collaboration | GitHub with small commits, and a group chat |
| Report and slides | Google Docs or Word exported to PDF, and PowerPoint |

```
otw-practicum/
  engine/        game_state.py
  agents/        random_agent.py, ucs_agent.py, minimax_agent.py, alphabeta_agent.py
  experiments/   tournament.py, plots.py
  maps/          build_map.py, its_sukolilo.json
  web/           index.html, game.js, style.css, replays/
  logs/
  docs/          interface.md
  server.py
  requirements.txt
  README.md
```

## 9. Experiments (Chapter 3)

1. **Pruning study:** nodes expanded and time per move, Minimax vs. Alpha-Beta, at depths 2 to 5.
2. **Equal time budget:** the depth each reaches in the same time, and the resulting win rate.
3. **Difficulty check:** Proctor win rate for UCS, Minimax, and Alpha-Beta against the Greedy and Random simulated Students, over 100 or more random start pairs each.
4. **Depth study:** Minimax win rate and time per move at depths 1 to 5.
5. **Human playtest:** 5 or more classmates play each difficulty a few times. Record the win rate and a 1 to 5 difficulty rating.

Report win rate, average game length, nodes expanded, and time per move. Seed everything so results can be reproduced.

## 10. Report and presentation

**Report (PDF)**

- **Cover page:** title, course, team names and IDs
- **Chapter 1:** background, problem statement, and benefits
- **Chapter 2:** rules, state space, algorithms with pseudocode, evaluation function, architecture, and map dataset
- **Chapter 3:** experiments, plots, discussion of why each algorithm performed as it did, and the GitHub link
- **Chapter 4:** conclusion, limitations, and future work (for example MCTS, or more maps)
- **References**

**Presentation (15 minutes maximum)**

| Slides | Content | Time |
| --- | --- | --- |
| 1 | Title and team | 0:30 |
| 2 to 3 | Background, problem, and benefits | 2:00 |
| 4 to 5 | Game rules and architecture | 2:00 |
| 6 to 7 | The three algorithms | 3:00 |
| 8 to 10 | Results and discussion | 4:00 |
| 11 | Live demo (under 2 minutes) | 2:00 |
| 12 | Conclusion and future work | 1:30 |

## 11. Risks and final checklist

| Risk | Fix |
| --- | --- |
| FE waits for BE | Use a mock API from Day 1 |
| Flask does not run on GitHub Pages | Run Flask on a laptop, and keep a demo video as the fallback |
| Hard is too slow | Use the 1-second time limit with iterative deepening |
| One side always wins | Tune the turn limit T on Day 2 |
| Rules change mid-project | Freeze the rule table in section 1 on Day 1 |
| Scope creep | Build only what this guide lists |

- [ ] Report PDF with all chapters, cover page, and references
- [ ] GitHub link in Chapter 3, with a README that runs
- [ ] Slides under 15 minutes
- [ ] Three algorithms implemented and compared
- [ ] Results reproducible (seeds set, logs saved)
- [ ] Demo tested, with the video fallback ready
- [ ] Every member can explain the whole system
