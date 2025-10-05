import time, os, math, random

print("Modules imported!")
time.sleep(0.3)

play = "yes"
location = "menu"
time_intill_kill = int(15)
kill_time = int(0)
kill_location= 0

# Rlobal Rooms #
global place_kitchen
global place_livingroom
global place_bedroom
global place_bathroom
place_kitchen = "Kitchen"
place_livingroom = "Livingroom"
place_bedroom = " Bedroom"
place_bathroom = "Bathroom"
# Global Rooms #

def sleep(sleep_time):
    time.sleep(sleep_time)
def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

# Locations #
def start_game():#                                               start_game()
    global location
    kill_start() # start kill system
    location = "menu"
    print(f"Your currently near the {location}")
    sleep(3)
    clear_terminal()
    move_location(location)
def menu():
    clear_terminal()
    print("Murder Mystery | By Sa1")
    print(" ") #                                                      menu()
    print("Start")
    print("Settings")
    print("Profile")
    print("Help")
    print("Quit")
    menu_selection = str(input("What option do you want to pick?: ")).lower()
    if menu_selection == "start":
        start_game()#                                                menu_selection()
def location_kitchen():
    print("You step in to the kitchen and see a clean cutting board on the marbled counter")
    if kill_location == 1:
        print("...")
    sleep(1)
    move_location()
def location_livingroom():
    print("You step in to the living room and see a knocked over lamp and a blood stain")
    if kill_location == 2:
        print("...")
    sleep(1)
    move_location(location)
def location_bedroom():
    print("Your step into the bedroom and see a unmade bed with pillows all over the floor")
    if kill_location == 3:
        print("...")
    sleep(1)
    move_location(location)
def location_bathroom():
    print("You step into the bathroom and see blood stains on the carpet")
    if kill_location == 4:
        print("...")
    sleep(1)
    move_location(location)
def move_location(location):
    print("\nLocations:")
    print(f"Kitchen - {'(You are currently here)' if location == 'kitchen' else ''}")
    print(f"Livingroom - {'(You are currently here)' if location == 'livingroom' else ''}")
    print(f"Bedroom - {'(You are currently here)' if location == 'bedroom' else ''}")
    print(f"Bathroom - {'(You are currently here)' if location == 'bathroom' else ''}")
    location = str(input("Where would you like to go?: ")).lower()
    if location == "kitchen":
        location_kitchen()
    elif location == "livingroom":
        location_livingroom()
    elif location == "bedroom":
        location_bedroom()
    elif location == "bathroom":
        location_bathroom()
    else:
        menu()
def kill_start():
    global kill_location
    kill_location = random.randint(1, 4)
    

# Basic Movment and killing ^ #














# Run Script #

menu()

# Run Script #