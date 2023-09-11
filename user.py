import jsonpickle

import util
from state import State
from transaction import Transaction


class User:

    def __init__(self, state, balance=0):
        """
        Initialize a new User with an Ethereum address and private key.
        """
        self.state = state
        self.private_key, self.public_key, self.address = util.generate_keypair()
        self.balance = balance  # Initial balance, can be adjusted based on requirements.
        self.transaction_history = []  # List to store all transactions initiated by the user.
        self.nonce = 0  # Track the number of transactions sent by the user.

    def send_transaction(self, receiver, amount):
        """
        Send a transaction from this user to a receiver.
        
        Parameters:
        - receiver: User object representing the receiver of the transaction.
        - amount: Amount of currency to be transferred.
        
        Returns:
        - Transaction object if successful, None otherwise.
        """

        if self.balance < amount:
            print("Insufficient balance.")
            print(f"User {self.public_key} has insufficient balance. Balance: {self.balance}, Amount: {amount}")

            return None

        # Create a new transaction with the current nonce.
        transaction = Transaction(self, receiver, amount, self.nonce, self.state)

        # Validate the transaction before processing it.
        # valid, message = transaction.validate()

        # Validate the created transaction.
        valid, message = transaction.validate()
        if valid:
            self.nonce += 1
            # Sign the transaction before validating and processing it.
            transaction.sign_transaction(self.private_key)
        else:
            print(f"Transaction failed:", message)
            return None

        # If the transaction is valid, process it.
        transaction.process()

        # Append the processed transaction to the user's transaction history.
        self.transaction_history.append(transaction)

        return transaction

    def get_balance(self):
        """
        Get the current balance of the user.
        
        Returns:
        - The balance of the user.
        """

        return self.balance

    def get_nonce(self):
        """
        Get the current nonce value of the user.
        
        Returns:
        - The nonce value of the user.
        """

        return self.nonce
    def to_dict(self):
        return jsonpickle.encode(self)

    @classmethod
    def from_dict(cls, data):
        return jsonpickle.decode(data)
