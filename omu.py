import curses

# Main map with entrances marked as '#' (accessible positions)
main_map = [
    list("|=================================================================================================================================|"),
    list("|            |              |              |                                  |                                                   |"),
    list("|            |              |              |                                  |                                                   |"),
    list("|            |              #              #                                  |                                                   |"),
    list("|            |              #              #                                  |                                                   |"),
    list("|            |              |              |                                  |                                                   |"),
    list("|            {==============}              {==================================|====================##=============================|"),
    list("|                                                                                                               |"),
    list("|                                                                                                               |"),
    list("|                                                                                                               |"),
    list("|                                                                                                               |"),
    list("|                                                                                                               |"),
    list("|                                           {=========##======================|===============##================|"),
    list("|------------------------                   |                                 |                                 |"),
    list("|                                           |                                 |                                 |"),
    list("|                                           |                                 |                                 |"),
    list("|===============}                           |                                 |                                 |"),
    list("|               |                           |                                 |                                 |"),
    list("|               #                           |                                 |                                 |"),
    list("|               #                           |                                 |                                 |"),
    list("|===============|===========================|=================================|=================================|"),
]

# Pad all rows in main_map to the same length
# Find all groups of adjacent entrances and assign them to
for i, row in enumerate(main_map):
    if len(row) < max_main_map_len:
        main_map[i] += [' '] * (max_main_map_len - len(row))

# Room maps
def make_room_map(room_num):
    return [
        list("|_____________|"),
        list("|             |"),
        list(f"|   ROOM {room_num}    |"),
        list("|             |"),
        list("|             |"),
        list("|      <      |"),
        list("|_____________|"),
    ]

maps = {'main': main_map}
for i in range(1, 9):
    maps[f'room{i}'] = make_room_map(i)

current_map_key = 'main'
dungeon_map = maps[current_map_key]

# Dynamically find exits in room maps
def find_room_exit(room_map):
    for r, row in enumerate(room_map):
        for c, ch in enumerate(row):
            if ch == '<':
                return (r, c)
    return None

# Dynamically find entrances on main map and assign rooms
def find_entrances():
    entrances = {}
    room_idx = 1
    for r, row in enumerate(main_map):
        for c, ch in enumerate(row):
            if ch == '#':
                entrances[(r, c)] = f'room{room_idx}'
                room_idx += 1
                if room_idx > 8:
                    break
        if room_idx > 8:
            break
    return entrances

entrances = find_entrances()

# Find exits for each room and store in room_exits
room_exits = {}
for key in maps:
    if key != 'main':
        room_exits[key] = find_room_exit(maps[key])

# Store last position for each map
player_positions = {}
for key, m in maps.items():
    # Find a valid starting position (not a wall or entrance)
    found = False
    for r, row in enumerate(m):
        for c, ch in enumerate(row):
            if ch not in ('#', '|', '=', '-', '_', '<'):
                player_positions[key] = [r, c]
                found = True
                break
        if found:
            break
    if not found:
        player_positions[key] = [1, 1]  # fallback
player_pos = player_positions['main'][:]  # copy starting position

def draw_map(stdscr):
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    for r, row in enumerate(dungeon_map):
        if r >= max_y - 1:
            break
        for c, ch in enumerate(row):
            if c >= max_x:
                break
            try:
                # Ensure player_pos is within bounds
                if [r, c] == player_pos and 0 <= r < max_y and 0 <= c < max_x:
                    stdscr.addch(r, c, ord('@'), curses.color_pair(2))
                else:
                    if ch in ('#', '|', '_'):
                        stdscr.addch(r, c, ord(ch), curses.color_pair(1))
                    elif ch == '<':
                        stdscr.addch(r, c, ord(ch), curses.color_pair(3))
                    else:
                        stdscr.addch(r, c, ord(ch), curses.color_pair(0))
            except curses.error:
                pass

def is_adjacent_to_entrance(r, c):
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r + dr, c + dc
        if (nr, nc) in entrances and dungeon_map[nr][nc] == '#':
            return entrances[(nr, nc)]
    return None

def is_adjacent_to_exit(r, c, room_key):
    exit_pos = room_exits.get(room_key)
    if not exit_pos:
        return False
    er, ec = exit_pos
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        if [r + dr, c + dc] == [er, ec]:
            return True
    return False

def enter_room(room_name):
    global dungeon_map, current_map_key, player_pos
    # Save current position
    player_positions[current_map_key] = player_pos[:]
    current_map_key = room_name
    dungeon_map = maps[room_name]
    player_pos[:] = player_positions[room_name][:]

def return_to_main():
    global dungeon_map, current_map_key, player_pos
    # Save current position
    player_positions[current_map_key] = player_pos[:]
    current_map_key = 'main'
    dungeon_map = maps['main']
    player_pos[:] = player_positions['main'][:]

def main(stdscr):
    global player_pos

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)

def can_move_to(r, c):
    # Check bounds
    if r < 0 or r >= len(dungeon_map) or c < 0 or c >= len(dungeon_map[0]):
        return False
    ch = dungeon_map[r][c]
    # Prevent moving into walls and entrances
    if ch in ('|', '=', '-', '_', '#'):
        return False
    return True

def main(stdscr):
    global player_pos

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)   # Walls and entrances
    curses.init_pair(2, curses.COLOR_YELLOW, -1)  # Player
    curses.init_pair(3, curses.COLOR_CYAN, -1)    # Exits

    while True:
        draw_map(stdscr)
        max_y, max_x = stdscr.getmaxyx()
        status = "Move: w/a/s/d, interact: e, quit: q"
        r, c = player_pos
        stdscr.addstr(max_y - 1, 0, status[:max_x-1])
        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == ord('w') and can_move_to(r - 1, c):
            player_pos[0] -= 1
        elif key == ord('s') and can_move_to(r + 1, c):
            player_pos[0] += 1
        elif key == ord('a') and can_move_to(r, c - 1):
            player_pos[1] -= 1
        elif key == ord('d') and can_move_to(r, c + 1):
            player_pos[1] += 1
        elif key == ord('e'):
            if current_map_key == 'main':
                room = is_adjacent_to_entrance(r, c)
                if room:
                    enter_room(room)
            else:
                if is_adjacent_to_exit(r, c, current_map_key):
                    return_to_main()

curses.wrapper(main)
