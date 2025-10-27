class client:
    def __init__(self, name, credits):
        self.name = name
        self.__credits = credits

    @property
    def credits(self):
        return self.__credits
    
    @credits.setter
    def credits(self, value):
        if value >= 0:
            self.__credits = value
        else:
            raise ValueError("Credits cannot be negative")
    
    @
    