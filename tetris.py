import curses
import random
import time

# Tetris shapes (rotations)
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[0, 1, 0], [1, 1, 1]],  # T
    [[1, 0, 0], [1, 1, 1]],  # J
    [[0, 0, 1], [1, 1, 1]],  # L
    [[1, 1, 0], [0, 1, 1]],  # S
    [[0, 1, 1], [1, 1, 0]],  # Z
]

BOARD_WIDTH = 10
BOARD_HEIGHT = 20

def rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]

def rotate_ccw(shape):
    return [list(row) for row in zip(*shape)][::-1]

def create_board():
    return [[0] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]

def draw_board(stdscr, board, piece, pos):
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    # Draw border
    top = 0
    left = 0
    right = BOARD_WIDTH * 2
    bottom = BOARD_HEIGHT
    for y in range(top, bottom + 1):
        if left < max_x:
            stdscr.addstr(y, left, "|")
        if right < max_x:
            stdscr.addstr(y, right, "|")
    for x in range(left, right + 1, 2):
        if top < max_y:
            stdscr.addstr(top, x, "-")
        if bottom < max_y:
            stdscr.addstr(bottom, x, "-")
    # Draw board
    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            if y + 1 < max_y and x * 2 + 1 < max_x:
                if cell:
                    stdscr.addstr(y + 1, x * 2 + 1, "[]")
                else:
                    stdscr.addstr(y + 1, x * 2 + 1, "  ")
    # Draw current piece
    for py, row in enumerate(piece):
        for px, cell in enumerate(row):
            by, bx = pos[0] + py, pos[1] + px
            if cell and 0 <= by < BOARD_HEIGHT and 0 <= bx < BOARD_WIDTH:
                if by + 1 < max_y and bx * 2 + 1 < max_x:
                    stdscr.addstr(by + 1, bx * 2 + 1, "[]", curses.A_REVERSE)
    stdscr.refresh()

def valid_position(board, piece, pos):
    for py, row in enumerate(piece):
        for px, cell in enumerate(row):
            if cell:
                by, bx = pos[0] + py, pos[1] + px
                if bx < 0 or bx >= BOARD_WIDTH or by < 0 or by >= BOARD_HEIGHT:
                    return False
                if board[by][bx]:
                    return False
    return True

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    board = create_board()
    piece = random.choice(SHAPES)
    pos = [0, BOARD_WIDTH // 2 - len(piece[0]) // 2]
    fall_time = 0.5
    last_fall = time.time()

    while True:
        draw_board(stdscr, board, piece, pos)
        key = stdscr.getch()
        new_pos = pos[:]
        new_piece = [row[:] for row in piece]
        if key == ord('q'):
            break
        elif key == curses.KEY_LEFT:
            new_pos[1] -= 1
        elif key == curses.KEY_RIGHT:
            new_pos[1] += 1
        elif key == curses.KEY_DOWN:
            new_pos[0] += 1
        elif key == ord(' '):  # rotate clockwise
            rotated = rotate(piece)
            if valid_position(board, rotated, pos):
                piece = rotated
        elif key == ord('r'):  # rotate counter-clockwise
            rotated = rotate_ccw(piece)
            if valid_position(board, rotated, pos):
                piece = rotated
        # Move piece if valid
        if valid_position(board, piece, new_pos):
            pos = new_pos
        # Piece falls
        if time.time() - last_fall > fall_time:
            if valid_position(board, piece, [pos[0] + 1, pos[1]]):
                pos[0] += 1
            else:
                # Lock piece
                for py, row in enumerate(piece):
                    for px, cell in enumerate(row):
                        if cell:
                            by, bx = pos[0] + py, pos[1] + px
                            if 0 <= by < BOARD_HEIGHT and 0 <= bx < BOARD_WIDTH:
                                board[by][bx] = 1
                # Clear full lines
                board[:] = [row for row in board if not all(cell == 1 for cell in row)]
                while len(board) < BOARD_HEIGHT:
                    board.insert(0, [0] * BOARD_WIDTH)
                # New piece
                piece = random.choice(SHAPES)
                pos = [0, BOARD_WIDTH // 2 - len(piece[0]) // 2]
            last_fall = time.time()
        time.sleep(0.05)

if __name__ == "__main__":
    curses.wrapper(main)
