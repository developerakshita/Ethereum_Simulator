# To manage all the account balances and nonces.
import jsonpickle
class State:
    def __init__(self, balances, nonces):
        # Dictionary to store balances. Key: Address, Value: Balance
        self.balances = balances
        # Dictionary to store nonces. Key: Address, Value: Nonce
        self.nonces = nonces

    def to_dict(self):
        return jsonpickle.encode(self)

    @classmethod
    def from_dict(cls, data):
        return jsonpickle.decode(data)

    def get_balance(self, address):
        """Retrieve the balance for an address. If address is not found, balance is assumed to be 0."""
        return self.balances.get(address, 0)

    def set_balance(self, address, amount):
        """Set the balance for an address."""
        self.balances[address] = amount

    def get_nonce(self, address):
        """Retrieve the nonce for an address. If address is not found, nonce is assumed to be 0."""
        return self.nonces.get(address, 0)

    def set_nonce(self, address, nonce):
        """Set the nonce for an address."""
        self.nonces[address] = nonce

    def process_transaction(self, transaction):
        """Process a transaction, updating state."""
        sender = transaction.sender.address
        receiver = transaction.receiver.address
        amount = transaction.amount

        # Deduct amount from sender and add to receiver
        self.balances[sender] = self.get_balance(sender) - amount
        self.balances[receiver] = self.get_balance(receiver) + amount

        # Increment nonce for sender
        self.set_nonce(sender, self.get_nonce(sender) + 1)
