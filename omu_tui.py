#!/usr/bin/env python3
import curses
import random
import time
import heapq
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set

# Among-Us-like single-player terminal game using curses with improved bot pathfinding (A*)
# Two-phase bot movement prevents overlap/swap; meeting/report prompt is clearer.

Point = Tuple[int, int]  # (y, x)

HELP_TEXT = [
    "Controls: Arrow Keys / WASD to move, E to start/stop task, R to report, H to toggle help, Q to quit",
    "Goal: Complete all tasks (stand on 'T' and press E) or eject the impostor after reporting.",
    "Bots: A* pathfinding to targets; no passing through each other; no oscillating back-and-forth.",
]

@dataclass
class Entity:
    name: str
    y: int
    x: int
    alive: bool = True
    char: str = "C"  # Player '@', Crewmates 'C'; roles hidden
    color_pair: int = 0

# eq=False keeps default object identity equality and default hash, so NPCs are hashable and usable in sets/dicts
@dataclass(eq=False)
class NPC(Entity):
    role: str = "crewmate"  # or "impostor"
    last_move_time: float = 0.0
    kill_cooldown: float = 0.0
    assigned_task: Optional[Point] = None
    patrol_target: Optional[Point] = None
    current_target: Optional[Point] = None
    current_path: List[Point] = field(default_factory=list)  # list of steps to goal (excluding current pos)
    last_pos: Optional[Point] = None
    repath_after: float = 0.0  # time after which we allow re-path even if target unchanged

@dataclass
class Corpse:
    victim_name: str
    y: int
    x: int
    discovered: bool = False

class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr

        # Generate a spacious map with wide corridors and rooms
        self.height = 24
        self.width = 64
        self.map = self.generate_map(self.width, self.height, corridor_w=3, room_count=(5, 7))

        # Walkable tiles are anything not a wall '#'
        self.walkable: Set[Point] = set(
            (y, x) for y in range(self.height) for x in range(self.width) if self.map[y][x] != '#'
        )

        # Extract tasks from map ('T')
        self.tasks: Dict[Point, float] = {}  # progress 0..1
        for y in range(self.height):
            for x in range(self.width):
                if self.map[y][x] == 'T':
                    self.tasks[(y, x)] = 0.0

        # Player start: free tile near center
        py, px = self.find_free_tile_near_center()
        self.player = Entity(name="You", y=py, x=px, char='@')
        self.player_role = "crewmate"

        # Bots
        bot_names = ["Cyan", "Lime", "Purple", "Orange", "Blue", "Pink", "Brown", "Yellow"]
        random.shuffle(bot_names)
        bot_count = 6
        self.npcs: List[NPC] = []
        starts = self.spawn_points(bot_count)
        for i in range(bot_count):
            ny, nx = starts[i]
            npc = NPC(
                name=bot_names[i % len(bot_names)],
                y=ny, x=nx,
                char='C',
                role="crewmate",
                color_pair=0,  # fixed: pass keyword, not a function call
            )
            self.npcs.append(npc)
        # Pick 1 impostor
        if self.npcs:
            random.choice(self.npcs).role = "impostor"

        self.corpses: List[Corpse] = []

        # Time control
        self.last_update = time.time()
        self.tick_rate = 1.0 / 16.0  # 16 FPS
        self.bot_move_interval = 0.12  # step interval
        self.impostor_kill_range = 1
        self.impostor_kill_cooldown_time = 7.0

        self.running = True
        self.show_help = True

        # Meetings
        self.meeting_mode = False
        self.meeting_message = ""
        self.meeting_selection_idx = 0
        self.meeting_candidates: List[NPC] = []
        self.meeting_skip_option = True

        # Colors
        self.setup_colors()

        # Task interaction
        self.in_task = False
        self.task_target: Optional[Point] = None
        self.task_progress_rate = 0.02  # per tick while in task

        # Intersections for patrols
        self.intersections: List[Point] = self.compute_intersections()

    # ---------------- Colors ----------------
    def setup_colors(self):
        try:
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_BLACK, -1)   # walls / border
                curses.init_pair(2, curses.COLOR_CYAN, -1)    # player
                curses.init_pair(3, curses.COLOR_WHITE, -1)   # crewmate npc
                curses.init_pair(4, curses.COLOR_YELLOW, -1)  # tasks
                curses.init_pair(5, curses.COLOR_RED, -1)     # corpse
                curses.init_pair(6, curses.COLOR_GREEN, -1)   # hud
                curses.init_pair(7, curses.COLOR_MAGENTA, -1) # meeting UI
        except curses.error:
            pass

    # ---------------- Map generation and utilities ----------------

    def generate_map(self, width: int, height: int, corridor_w: int = 3, room_count: Tuple[int, int] = (5, 7)) -> List[List[str]]:
        rnd = random.Random()
        rnd.seed()
        grid = [['#' for _ in range(width)] for _ in range(height)]

        def carve_rect(y1, x1, y2, x2, ch='.'):
            for y in range(max(1, y1), min(height-1, y2+1)):
                for x in range(max(1, x1), min(width-1, x2+1)):
                    grid[y][x] = ch

        rooms: List[Tuple[int, int, int, int]] = []
        target_rooms = rnd.randint(room_count[0], room_count[1])
        attempts = 0
        while len(rooms) < target_rooms and attempts < 200:
            attempts += 1
            rw = rnd.randint(8, 14)
            rh = rnd.randint(5, 8)
            rx = rnd.randint(2, width - rw - 3)
            ry = rnd.randint(2, height - rh - 3)
            new_room = (ry, rx, ry + rh, rx + rw)
            def overlaps(a, b):
                ay1, ax1, ay2, ax2 = a
                by1, bx1, by2, bx2 = b
                return not (ay2+2 < by1 or by2+2 < ay1 or ax2+2 < bx1 or bx2+2 < ax1)
            if any(overlaps(new_room, r) for r in rooms):
                continue
            rooms.append(new_room)
            carve_rect(*new_room, ch='.')

        if rooms:
            centers = [((r[0]+r[2])//2, (r[1]+r[3])//2) for r in rooms]
            remaining = set(range(1, len(centers)))
            connected = {0}
            def carve_horiz(y, x1, x2):
                if x1 > x2: x1, x2 = x2, x1
                for x in range(x1, x2+1):
                    for dy in range(-(corridor_w//2), (corridor_w//2)+1):
                        yy = y + dy
                        if 1 <= yy < height-1 and 1 <= x < width-1:
                            grid[yy][x] = '.'
            def carve_vert(x, y1, y2):
                if y1 > y2: y1, y2 = y2, y1
                for y in range(y1, y2+1):
                    for dx in range(-(corridor_w//2), (corridor_w//2)+1):
                        xx = x + dx
                        if 1 <= y < height-1 and 1 <= xx < width-1:
                            grid[y][xx] = '.'
            while remaining:
                best = None
                for j in remaining:
                    yj, xj = centers[j]
                    for i in connected:
                        yi, xi = centers[i]
                        d = abs(yi - yj) + abs(xi - xj)
                        if best is None or d < best[0]:
                            best = (d, i, j)
                _, i, j = best
                ci, cj = centers[i], centers[j]
                if random.random() < 0.5:
                    carve_horiz(ci[0], ci[1], cj[1])
                    carve_vert(cj[1], ci[0], cj[0])
                else:
                    carve_vert(ci[1], ci[0], cj[0])
                    carve_horiz(cj[0], ci[1], cj[1])
                connected.add(j)
                remaining.remove(j)

        floor = [(y, x) for y in range(2, height-2) for x in range(2, width-2) if grid[y][x] == '.']
        random.shuffle(floor)
        for (ty, tx) in floor[:8]:
            grid[ty][tx] = 'T'
        return grid

    def is_in_bounds(self, y: int, x: int) -> bool:
        return 0 <= y < self.height and 0 <= x < self.width

    def is_walkable(self, y: int, x: int) -> bool:
        return self.is_in_bounds(y, x) and self.map[y][x] != '#'

    def is_wall(self, y: int, x: int) -> bool:
        return self.is_in_bounds(y, x) and self.map[y][x] == '#'

    def compute_intersections(self) -> List[Point]:
        inter = []
        for y in range(1, self.height-1):
            for x in range(1, self.width-1):
                if not self.is_walkable(y, x):
                    continue
                deg = sum(1 for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)] if self.is_walkable(y+dy, x+dx))
                if deg >= 3:
                    inter.append((y, x))
        return inter

    # ---------------- Spawning and utility ----------------

    def find_free_tile_near_center(self) -> Point:
        cy, cx = self.height // 2, self.width // 2
        q = deque([(cy, cx)])
        seen = {(cy, cx)}
        while q:
            y, x = q.popleft()
            if self.is_walkable(y, x) and self.map[y][x] != 'T':
                return (y, x)
            for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                ny, nx = y+dy, x+dx
                if self.is_in_bounds(ny, nx) and (ny, nx) not in seen:
                    seen.add((ny, nx)); q.append((ny, nx))
        for y in range(self.height):
            for x in range(self.width):
                if self.is_walkable(y, x) and self.map[y][x] != 'T':
                    return (y, x)
        return (1, 1)

    def spawn_points(self, n: int) -> List[Point]:
        free = [(y, x) for (y, x) in self.walkable if self.map[y][x] != 'T']
        random.shuffle(free)
        return free[:n]

    def entity_at(self, y: int, x: int) -> Optional[Entity]:
        if self.player.alive and (y, x) == (self.player.y, self.player.x):
            return self.player
        for n in self.npcs:
            if n.alive and (y, x) == (n.y, n.x):
                return n
        return None

    # ---------------- Input ----------------

    def handle_input(self):
        try:
            ch = self.stdscr.getch()
        except Exception:
            return
        if ch == -1:
            return

        if self.meeting_mode:
            self.handle_meeting_input(ch)
            return

        if ch in (ord('h'), ord('H')):
            self.show_help = not self.show_help
            return

        if ch in (ord('q'), ord('Q')):
            self.running = False
            return

        if ch in (ord('e'), ord('E')):
            pt = (self.player.y, self.player.x)
            if self.in_task:
                self.in_task = False
                self.task_target = None
            elif pt in self.tasks:
                self.in_task = True
                self.task_target = pt
            return

        if ch in (ord('r'), ord('R'), ord(' ')):  # Space also reports
            if self.near_corpse(self.player.y, self.player.x):
                self.trigger_meeting()
            return

        dy = dx = 0
        if ch in (curses.KEY_UP, ord('w'), ord('W')): dy = -1
        elif ch in (curses.KEY_DOWN, ord('s'), ord('S')): dy = 1
        elif ch in (curses.KEY_LEFT, ord('a'), ord('A')): dx = -1
        elif ch in (curses.KEY_RIGHT, ord('d'), ord('D')): dx = 1

        if dy or dx:
            self.try_move_player(dy, dx)

    def try_move_player(self, dy: int, dx: int):
        if not self.player.alive:
            return
        if self.in_task:
            self.in_task = False
            self.task_target = None
        ny, nx = self.player.y + dy, self.player.x + dx
        if self.is_walkable(ny, nx) and not self.entity_at(ny, nx):
            self.player.y, self.player.x = ny, nx

    # ---------------- Update and AI ----------------

    def update(self, dt: float):
        if self.meeting_mode:
            return

        # Task progress
        if self.in_task:
            pt = self.task_target
            if pt is None or pt not in self.tasks or (self.player.y, self.player.x) != pt:
                self.in_task = False
                self.task_target = None
            else:
                prog = self.tasks[pt] + self.task_progress_rate
                if prog >= 1.0:
                    del self.tasks[pt]
                    self.in_task = False
                    self.task_target = None
                else:
                    self.tasks[pt] = prog

        now = time.time()

        # 1) Decide targets and paths for each NPC (no movement yet)
        intents: Dict[NPC, Point] = {}
        occupied_before: Set[Point] = set((n.y, n.x) for n in self.npcs if n.alive)
        occupied_before.add((self.player.y, self.player.x))

        for npc in self.npcs:
            if not npc.alive:
                continue
            if now - npc.last_move_time < self.bot_move_interval:
                continue
            npc.last_move_time = now
            if npc.role == "impostor":
                npc.kill_cooldown = max(0.0, npc.kill_cooldown - (now - self.last_update))

            # Determine target
            target = self.choose_target(npc)
            if target != npc.current_target:
                npc.current_target = target
                npc.current_path = []
                npc.repath_after = 0.0

            # Decide step
            desired = (npc.y, npc.x)
            if target:
                # Re-path conditions: no path, path exhausted, path blocked, or timeout
                need_repath = False
                if not npc.current_path:
                    need_repath = True
                else:
                    step = npc.current_path[0]
                    if not self.is_walkable(step[0], step[1]):
                        need_repath = True
                    elif step in occupied_before and step != target:
                        need_repath = True
                if need_repath or now >= npc.repath_after:
                    npc.current_path = self.astar_path((npc.y, npc.x), target, blocked=occupied_before - {target})
                    npc.repath_after = now + 0.25

                if npc.current_path:
                    step = npc.current_path[0]
                    # Anti-oscillation: avoid stepping back to last_pos if we only have one-step progress
                    if npc.last_pos and step == npc.last_pos and len(npc.current_path) == 1:
                        npc.repath_after = now  # allow immediate re-path next tick
                        desired = (npc.y, npc.x)
                    else:
                        desired = step

            intents[npc] = desired

        # 2) Resolve conflicts: prevent overlaps and head-on swaps
        # Prevent moves onto player
        for npc in list(intents.keys()):
            if intents[npc] == (self.player.y, self.player.x):
                intents[npc] = (npc.y, npc.x)

        # Build reverse map desired -> npcs
        dest_map: Dict[Point, List[NPC]] = defaultdict(list)
        for n, pos in intents.items():
            dest_map[pos].append(n)

        staying_positions: Set[Point] = { (n.y, n.x) for n, pos in intents.items() if pos == (n.y, n.x) }

        approved: Set[NPC] = set()
        for pos, claimants in dest_map.items():
            if len(claimants) == 1:
                n = claimants[0]
                if pos in staying_positions and pos != (n.y, n.x):
                    continue  # cannot move into a staying occupant
                # head-on swap detection
                occupant = self.find_entity_at(pos)
                if isinstance(occupant, NPC):
                    occ_intent = intents.get(occupant, (occupant.y, occupant.x))
                    if occ_intent == (n.y, n.x):
                        continue  # block swap
                approved.add(n)
            else:
                # Multiple bots want the same tile; randomly pick one
                random.shuffle(claimants)
                approved.add(claimants[0])

        # 3) Commit moves
        for npc in self.npcs:
            if not npc.alive:
                continue
            desired = intents.get(npc, (npc.y, npc.x))
            if npc in approved and desired != (npc.y, npc.x):
                npc.last_pos = (npc.y, npc.x)
                npc.y, npc.x = desired
                if npc.current_path and npc.current_path[0] == desired:
                    npc.current_path.pop(0)

        # 4) Impostor kills after movement
        for npc in self.npcs:
            if not npc.alive or npc.role != "impostor":
                continue
            if npc.kill_cooldown > 0.0:
                continue
            victims: List[Entity] = []
            for ent in [self.player] + self.npcs:
                if ent is npc or not ent.alive:
                    continue
                if isinstance(ent, NPC) and ent.role == "impostor":
                    continue
                if abs(ent.y - npc.y) + abs(ent.x - npc.x) <= self.impostor_kill_range:
                    victims.append(ent)
            if victims:
                vic = random.choice(victims)
                self.kill_entity(vic)
                npc.kill_cooldown = self.impostor_kill_cooldown_time

        # Win/Lose conditions
        if not self.player.alive:
            self.game_over_screen(win=False, reason="You were eliminated by the impostor.")
            self.running = False
            return

        if len(self.tasks) == 0:
            self.game_over_screen(win=True, reason="All tasks completed! Crewmates win.")
            self.running = False
            return

        alive_crew = (1 if self.player.alive else 0) + sum(1 for n in self.npcs if n.alive and n.role == "crewmate")
        alive_impostors = sum(1 for n in self.npcs if n.alive and n.role == "impostor")
        if alive_impostors >= alive_crew and alive_impostors > 0:
            self.game_over_screen(win=False, reason="Impostor outnumbered crew. Impostor wins.")
            self.running = False
            return

        self.last_update = now

    def choose_target(self, npc: NPC) -> Optional[Point]:
        if npc.role == "impostor":
            # Hunt nearest living non-impostor entity (including player)
            candidates: List[Entity] = [self.player] + [n for n in self.npcs if n is not npc]
            candidates = [e for e in candidates if e.alive and not (isinstance(e, NPC) and e.role == "impostor")]
            if not candidates:
                return None
            return min(((e.y, e.x) for e in candidates), key=lambda p: abs(p[0]-npc.y)+abs(p[1]-npc.x))
        else:
            if npc.assigned_task and npc.assigned_task not in self.tasks:
                npc.assigned_task = None
            if npc.assigned_task is None:
                if self.tasks:
                    npc.assigned_task = min(self.tasks.keys(), key=lambda p: abs(p[0]-npc.y)+abs(p[1]-npc.x))
                else:
                    if npc.patrol_target is None or (npc.y, npc.x) == npc.patrol_target:
                        npc.patrol_target = self.choose_patrol_point(npc)
            return npc.assigned_task or npc.patrol_target

    def choose_patrol_point(self, npc: NPC) -> Point:
        if self.intersections:
            return random.choice(self.intersections)
        return random.choice(list(self.walkable))

    def near_corpse(self, y: int, x: int) -> bool:
        # On or adjacent (Manhattan 0 or 1)
        for c in self.corpses:
            if abs(c.y - y) + abs(c.x - x) <= 1:
                return True
        return False

    # ---------------- Pathfinding ----------------

    def astar_path(self, start: Point, goal: Point, blocked: Set[Point]) -> List[Point]:
        if start == goal:
            return []
        gy, gx = goal
        if not self.is_walkable(gy, gx):
            return []

        def h(p: Point) -> int:
            return abs(p[0] - gy) + abs(p[1] - gx)

        open_heap = []
        heapq.heappush(open_heap, (h(start), 0, start))
        came_from: Dict[Point, Optional[Point]] = {start: None}
        g_score: Dict[Point, int] = {start: 0}
        closed: Set[Point] = set()

        while open_heap:
            _, g, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
            if current == goal:
                break
            cy, cx = current
            for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                ny, nx = cy+dy, cx+dx
                nxt = (ny, nx)
                if not self.is_walkable(ny, nx):
                    continue
                if nxt in blocked and nxt != goal:
                    continue
                tentative_g = g + 1
                if tentative_g < g_score.get(nxt, 1_000_000_000):
                    g_score[nxt] = tentative_g
                    came_from[nxt] = current
                    f = tentative_g + h(nxt)
                    heapq.heappush(open_heap, (f, tentative_g, nxt))

        if goal not in came_from:
            return []

        # Reconstruct path (excluding start), result is [step1, step2, ..., goal]
        cur = goal
        rev: List[Point] = []
        while cur is not None and cur != start:
            rev.append(cur)
            cur = came_from[cur]
        rev.reverse()
        return rev

    # ---------------- Meetings ----------------

    def trigger_meeting(self):
        if not self.corpses:
            return
        self.meeting_mode = True
        self.meeting_message = "Body reported! Discuss and vote to eject a suspect."
        self.meeting_candidates = [n for n in self.npcs if n.alive]
        random.shuffle(self.meeting_candidates)
        self.meeting_selection_idx = 0

    def handle_meeting_input(self, ch: int):
        if ch in (curses.KEY_UP, ord('k'), ord('K')):
            self.meeting_selection_idx = max(0, self.meeting_selection_idx - 1)
        elif ch in (curses.KEY_DOWN, ord('j'), ord('J')):
            self.meeting_selection_idx = min(len(self.meeting_candidates), self.meeting_selection_idx + 1)  # include Skip
        elif ch in (10, 13, curses.KEY_ENTER, ord(' ')):  # Enter/Space to vote
            self.resolve_meeting_vote()
        elif ch in (ord('q'), ord('Q'), 27):
            self.meeting_mode = False
            self.corpses.clear()

    def resolve_meeting_vote(self):
        voted_out: Optional[NPC] = None
        player_vote_skip = (self.meeting_selection_idx == len(self.meeting_candidates))
        if not player_vote_skip and self.meeting_candidates:
            voted_out = self.meeting_candidates[self.meeting_selection_idx]

        voters = [n for n in self.npcs if n.alive]
        candidates = list(self.meeting_candidates)
        candidates_plus_skip: List[Optional[NPC]] = candidates + [None]

        votes: Dict[Optional[NPC], int] = defaultdict(int)
        votes[voted_out if not player_vote_skip else None] += 1  # player

        for voter in voters:
            weights = []
            total = 0.0
            for c in candidates_plus_skip:
                if c is None:
                    w = 0.9
                else:
                    w = 1.0 + (0.4 if c.role == "impostor" else 0.0)
                weights.append(w)
                total += w
            r = random.random() * total
            cum = 0.0
            choice = None
            for c, w in zip(candidates_plus_skip, weights):
                cum += w
                if r <= cum:
                    choice = c
                    break
            votes[choice] += 1

        top = sorted(votes.items(), key=lambda kv: (-kv[1], random.random()))
        choice, _ = top[0]
        if choice is None:
            self.meeting_message = "No one was ejected (skipped)."
        else:
            choice.alive = False
            if choice.role == "impostor":
                self.meeting_message = f"{choice.name} was an Impostor. Crewmates win!"
                self.render()
                self.game_over_screen(win=True, reason=self.meeting_message)
                self.running = False
                return
            else:
                self.meeting_message = f"{choice.name} was not an Impostor."

        self.corpses.clear()
        self.meeting_mode = False

    # ---------------- Rendering ----------------

    def render(self):
        self.stdscr.erase()
        maxy, maxx = self.stdscr.getmaxyx()
        if maxy < self.height + 4 or maxx < self.width + 2:
            msg = f"Please resize terminal to at least {self.width+2}x{self.height+4}. Current: {maxx}x{maxy}"
            self._safe_addstr(0, 0, msg[:max(1, maxx-1)])
            self.stdscr.refresh()
            return

        # Border
        for x in range(self.width + 2):
            self._safe_addch(0, x, ord('-'), curses.color_pair(1))
            self._safe_addch(self.height + 1, x, ord('-'), curses.color_pair(1))
        for y in range(self.height + 2):
            self._safe_addch(y, 0, ord('|'), curses.color_pair(1))
            self._safe_addch(y, self.width + 1, ord('|'), curses.color_pair(1))

        # Map with oriented wall glyphs
        for y in range(self.height):
            for x in range(self.width):
                ch = self.map[y][x]
                if ch == '#':
                    glyph = self.wall_glyph(y, x)
                    self._safe_addch(1 + y, 1 + x, ord(glyph), curses.color_pair(1))
                elif ch == 'T':
                    self._safe_addch(1 + y, 1 + x, ord('T'), curses.color_pair(4) | curses.A_BOLD)
                else:
                    self._safe_addch(1 + y, 1 + x, ord('.'))

        # Corpses
        for c in self.corpses:
            self._safe_addch(1 + c.y, 1 + c.x, ord('X'), curses.color_pair(5) | curses.A_BOLD)

        # NPCs
        for n in self.npcs:
            if not n.alive:
                continue
            color = curses.color_pair(3)
            self._safe_addch(1 + n.y, 1 + n.x, ord(n.char), color | curses.A_BOLD)

        # Player
        if self.player.alive:
            self._safe_addch(1 + self.player.y, 1 + self.player.x, ord(self.player.char), curses.color_pair(2) | curses.A_BOLD)

        # HUD
        tasks_left = len(self.tasks)
        bodies = len(self.corpses)
        crew_alive = sum(1 for n in self.npcs if n.alive and n.role == "crewmate") + (1 if self.player.alive else 0)
        impostors_alive = sum(1 for n in self.npcs if n.alive and n.role == "impostor")
        hud = f"Role: Crewmate | Tasks left: {tasks_left} | Bodies: {bodies} | Crew: {crew_alive} | Imp: {impostors_alive}"
        self._safe_addstr(1 + self.height, 1, hud[:self.width], curses.color_pair(6))

        # Report prompt if near a body
        if self.near_corpse(self.player.y, self.player.x):
            self._safe_addstr(2 + self.height, 1, "Body nearby: press R (or Space) to report", curses.color_pair(5))

        if self.in_task and self.task_target:
            prog = self.tasks.get(self.task_target, 0.0)
            barw = min(30, self.width - 2)
            filled = int(barw * prog)
            bar = "[" + "#" * filled + "-" * (barw - filled) + "]"
            self._safe_addstr(3 + self.height, 1, f"Task progress: {bar}  Press E to stop", curses.color_pair(4))

        if self.show_help and not self.meeting_mode:
            for i, line in enumerate(HELP_TEXT):
                if 4 + self.height + i < maxy:
                    self._safe_addstr(4 + self.height + i, 1, line[:self.width])

        if self.meeting_mode:
            self.render_meeting()

        self.stdscr.refresh()

    def wall_glyph(self, y: int, x: int) -> str:
        up = self.is_wall(y-1, x)
        down = self.is_wall(y+1, x)
        left = self.is_wall(y, x-1)
        right = self.is_wall(y, x+1)
        if up and down and not left and not right:
            return '|'
        if left and right and not up and not down:
            return '-'
        return '+'

    def render_meeting(self):
        maxy, maxx = self.stdscr.getmaxyx()
        win_w = min(50, maxx - 4)
        win_h = min(10 + len(self.meeting_candidates), maxy - 4)
        top = max((maxy - win_h)//2, 1)
        left = max((maxx - win_w)//2, 1)
        win = curses.newwin(win_h, win_w, top, left)
        win.box()
        title = "EMERGENCY MEETING"
        try:
            win.addstr(0, max(1, (win_w - len(title))//2), title, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass
        lines = [self.meeting_message, "Vote a suspect (Enter) or Skip. Use Up/Down. Q/Esc to skip."]
        for i, s in enumerate(lines):
            if 2 + i < win_h - 1:
                try:
                    win.addstr(2 + i, 2, s[:win_w-4])
                except curses.error:
                    pass

        items = [f"{i+1}. {n.name}" for i, n in enumerate(self.meeting_candidates)]
        items.append("Skip")
        sel = self.meeting_selection_idx
        for i, s in enumerate(items):
            y = 5 + i
            if y >= win_h - 1:
                break
            try:
                if i == sel:
                    win.addstr(y, 2, s[:win_w-4], curses.A_REVERSE)
                else:
                    win.addstr(y, 2, s[:win_w-4])
            except curses.error:
                pass

        win.refresh()

    # ---------------- Misc helpers ----------------

    def kill_entity(self, ent: Entity):
        ent.alive = False
        self.corpses.append(Corpse(victim_name=ent.name, y=ent.y, x=ent.x))

    def find_entity_at(self, pos: Point) -> Optional[Entity]:
        y, x = pos
        if (self.player.y, self.player.x) == pos and self.player.alive:
            return self.player
        for n in self.npcs:
            if n.alive and (n.y, n.x) == pos:
                return n
        return None

    def wrap_text(self, text: str, width: int) -> List[str]:
        words = text.split()
        lines = []
        cur = []
        cur_len = 0
        for w in words:
            add_len = len(w) + (1 if cur else 0)
            if cur_len + add_len > width:
                lines.append(" ".join(cur))
                cur = [w]
                cur_len = len(w)
            else:
                cur.append(w)
                cur_len += add_len
        if cur:
            lines.append(" ".join(cur))
        return lines

    def game_over_screen(self, win: bool, reason: str):
        self.stdscr.erase()
        maxy, maxx = self.stdscr.getmaxyx()
        msg = "Crewmates Win!" if win else "Impostor Wins!"
        sub = reason
        y = maxy // 2 - 1
        x = max(0, (maxx - len(msg)) // 2)
        try:
            self.stdscr.addstr(y, x, msg, curses.A_BOLD | curses.color_pair(6 if win else 5))
        except curses.error:
            pass
        y += 2
        for line in self.wrap_text(sub, max(10, maxx - 4)):
            x = max(0, (maxx - len(line)) // 2)
            try:
                self.stdscr.addstr(y, x, line)
            except curses.error:
                pass
            y += 1
            if y >= maxy - 2:
                break
        try:
            self.stdscr.addstr(maxy - 2, 2, "Press any key to exit...")
        except curses.error:
            pass
        self.stdscr.refresh()
        self.stdscr.nodelay(0)
        try:
            self.stdscr.getch()
        except Exception:
            pass
        self.stdscr.nodelay(1)

    def _safe_addch(self, y: int, x: int, ch: int, attrs: int = 0):
        try:
            self.stdscr.addch(y, x, ch, attrs)
        except curses.error:
            pass

    def _safe_addstr(self, y: int, x: int, s: str, attrs: int = 0):
        try:
            self.stdscr.addstr(y, x, s, attrs)
        except curses.error:
            pass

    def loop(self):
        self.stdscr.nodelay(1)
        self.stdscr.keypad(1)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.last_update = time.time()
        while self.running:
            now = time.time()
            dt = now - self.last_update
            if dt < self.tick_rate:
                time.sleep(self.tick_rate - dt)
                now = time.time()
                dt = now - self.last_update
            self.last_update = now

            self.handle_input()
            self.update(dt)
            self.render()

def main(stdscr):
    game = Game(stdscr)
    game.loop()

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass