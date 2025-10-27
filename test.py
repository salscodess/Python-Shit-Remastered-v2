class client:
    def __init__(self, name, credits):
        self.name = name
        self.__credits = credits

    @property
    def credit(self):
        return self.__credits

    @credit.setter
    def credit(self, value):
        if value <= 0:
            raise ValueError("Bad number")
        self.__credits = value

    @classmethod
    class FreeClient(Client):
    def __init__(self, name):
        super().__init__(name, credits=1000) 

if __name__ == "__main__":
    c1 = client.free("sal")
    print(c1.name,c1.credit)
    print(c1.support)