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
        play_dice = True
        while play_dice == True:
            clear_terminal()
            dice1 = random.randint(1,6)
            dice2 = random.randint(1,6)
            dice3 = random.randint(1,6)
            dice4 = random.randint(1,6)
            dice_result = dice1 + dice2
            dice_result2 = dice3 + dice4
            print(f"You rolled a {dice_result} and the computer rolled a {dice_result2}")
            if dice_result > dice_result2:
                print("You Won!")
            elif dice_result < dice_result2:
                print("You lost!")
            elif dice_result == dice_result2:
                print("It was a tie!")
            time.sleep(1.5)
            print("")
            play_dice_input = str(input("Continue? (Y or N): ")).lower()
            if play_dice_input == "n":
                play_dice = False
            clear_terminal()
    elif start == 2:
        print("--Settings--")
    elif start == 3:
        print("Bye")
        time.sleep(1.5)
        break
    else:
        print("Error")
clear_terminal()