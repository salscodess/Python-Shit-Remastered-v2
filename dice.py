import time, math, random, os

def clear_terminal():
    os.system('clear')

clear_terminal()

play = True

while play == True:
    print("1: Start")
    print("2: Settings")
    print("3: Quit")
    start = int(input(": "))
    if start == 1:
        print("...")
    elif start == 2:
        print("...")
    elif start == 3:
        print("Bye")
        time.sleep(1.5)
        break
    else:
        print("Error")
clear_terminal()