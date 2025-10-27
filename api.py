import requests, time, random, os


wait_time = 0
def sleep(wait_time):
    time.sleep(wait_time)
def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

key = "DEFAULT-KEY-123"
ip = "111.11.111.111"
param1 = "version"
param2 = "0"
Params = {param1: param2}
data = {
    "key": key,
    "ip": ip,
    "params": Params
}

Start = True
while Start == True:
    print("""Choose an option:

    1: Open Commands
    2: Info
    3: Debug
    4: Exit """)
    option = str(input(""))

    if option == "1":
        clear_terminal()
        print("Menu Commands")
        print("1: Open Command 1")
        print("2: Open Command 2")
        print("3: Open Command 3")
        print("4: Back to Main Menu")
        command = int(input(""))
        if command == 1:
            sleep(1)
            param1 = "version"
            param2 = "info"
            Params = {param1: param2}  # Update Params dict
            data["params"] = Params     # Update data dict
            r = requests.post("http://178.63.206.189:8000/command", json=data)
            print(data)
            print("")
            print(r.text)
    elif option == "2":
            sleep(1)
            param1 = "version"
            param2 = "info"
            Params = {param1: param2}  # Update Params dict
            data["params"] = Params     # Update data dict
            r = requests.post("http://178.63.206.189:8000/command", json=data)
            print(data)
            print("")
            print(r.text)
    elif option == "3":
        print("idk")
    elif option == "4":
        print("Exiting...")
        Start = False
