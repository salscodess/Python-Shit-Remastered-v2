# =============================
#  Subscription & Credit System
#  Object-Oriented Programming Practice
# =============================

# Parent class (Base Client)
class Client:
    # __init__ runs when you create a new client
    # name: client's name, credits: starting credits
    def __init__(self, name, credits):
        self.name = name
        self.__credits = credits  # private variable (hidden / protected)

    # Property = acts like a variable, but actually calls a function
    @property
    def credits(self):
        return self.__credits  # safe read-only access

    # Setter = safe way to modify private data
    @credits.setter
    def credits(self, value):
        if value < 0:
            raise ValueError("Credits cannot be negative")
        self.__credits = value

    # Method to deduct credits if enough exist
    # Returns True/False to indicate success/failure
    def use_credit(self, cost=1):
        if self.__credits >= cost:
            self.__credits -= cost
            return True
        return False


# =============================
# Subscription Tiers (Inheritance)
# =============================

# Free users - lowest limits
class FreeClient(Client):
    def __init__(self, name):
        super().__init__(name, credits=1000)  # call parent class
        self.rate_limit = 60  # requests per minute
        self.support = "Basic"  # support level


# Pro users - higher limits
class ProClient(Client):
    def __init__(self, name):
        super().__init__(name, credits=100000)
        self.rate_limit = 600
        self.support = "Priority"


# Enterprise users - biggest limits & perk
class EnterpriseClient(Client):
    def __init__(self, name):
        super().__init__(name, credits=10000000)
        self.rate_limit = 5000
        self.support = "Dedicated"


# =============================
# Testing the System
# =============================
if __name__ == "__main__":
    # Create one client from each tier
    free = FreeClient("StarterCo")
    pro = ProClient("DevTeam")
    enterprise = EnterpriseClient("BigBusiness")

    # Demonstrate credits + security
    print("=== Credits Check ===")
    print(f"{free.name}: {free.credits} credits")
    print(f"{pro.name}: {pro.credits} credits")
    print(f"{enterprise.name}: {enterprise.credits} credits")

    # Spend credits
    print("\n=== Spending Credits ===")
    free.use_credit()  # spend 1
    print(f"After spending, {free.name}: {free.credits} credits")

    # Testing validation: uncomment to see failure
    # free.credits = -50  # This would raise an exception

    # Subscription benefits
    print("\n=== Subscription Perks ===")
    print(f"{pro.name} support level: {pro.support}")
    print(f"{enterprise.name} rate limit: {enterprise.rate_limit} requests/min")

