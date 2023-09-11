import time
import uuid
from dataclasses import dataclass
import jsonpickle
from ecdsa import SigningKey, SECP256k1

WEI_IN_ETHER = 10 ** 18
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def ether_to_wei(ether_amount):
    """Convert an amount from Ether to Wei."""
    return int(ether_amount * WEI_IN_ETHER)


def wei_to_ether(wei_amount):
    """Convert an amount from Wei to Ether."""
    return wei_amount / WEI_IN_ETHER


class Transaction:
    def __init__(self, sender, receiver, amount, nonce, gas_price, gas_limit):
        """
        Initialize a new Transaction.

        Parameters:
        - sender: User object representing the sender of the transaction.
        - receiver: User object representing the receiver of the transaction.
        - amount: Amount of currency to be transferred in Wei.
        - nonce: Unique transaction number for sender's account.
        """
        self.transactionId = str(uuid.uuid4()).replace('-', '')
        self.sender = sender
        self.receiver = receiver
        self.amount = amount  # this amount is in Wei
        self.nonce = nonce
        self.signature = None
        self.gas_price = gas_price
        self.gas_limit = gas_limit
        self.timestamp = time.time()

    def serialize(self):
        """Convert the transaction data into a string representation."""
        return f"{self.transactionId}{self.sender}{self.receiver}{self.amount}{self.nonce}{self.gas_price}{self.gas_limit}"

    def sign_transaction(self, private_key):
        """Sign the transaction using the sender's private key."""
        serialized_data = self.serialize().encode('utf-8')

        # Use the sender's private key to sign the serialized transaction
        signing_key = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
        self.signature = signing_key.sign(serialized_data)

    def verify_signature(self):
        return True
        # """Verify the transaction signature using the sender's Ethereum address."""
        # serialized_data = self.serialize().encode('utf-8')
        # message_hash = sha3.keccak_256(serialized_data).digest()
        #
        # # Recover potential public keys from the signature
        # try:
        #     recovered_keys = VerifyingKey.from_public_key_recovery_with_digest(
        #         bytes.fromhex(self.signature),
        #         message_hash,
        #         curve=SECP256k1,
        #         sigdecode=sigdecode_string,
        #         hashfunc=sha3.keccak_256)
        # except Exception as e:
        #     # Failed to recover public keys
        #     return False
        #
        # # Check if any of the derived addresses from recovered keys match the sender's address
        # for key in recovered_keys:
        #     pubkey_bytes = key.to_string()
        #     derived_address = '0x' + sha3.keccak_256(pubkey_bytes).digest()[-20:].hex()
        #     if derived_address.lower() == self.sender.lower():
        #         return True
        #
        # return False

    def validate(self, state):
        # Check if the transaction amount is valid.
        if self.amount <= 0:
            return False, "Invalid transaction amount."

        # Check if sender has enough balance for the transaction.
        sender_balance = state.balances[self.sender]
        if sender_balance < self.amount:
            return False, "Insufficient balance."

        # Check the nonce to ensure the transaction is unique for the sender.
        sender_nonce = state.nonces[self.sender]
        if self.nonce <= sender_nonce:
            return False, "Invalid nonce."

        # Verify the transaction signature
        if not self.verify_signature():
            return False, "Invalid transaction signature."

        return True, "Transaction is valid."

    def to_dict(self):
        return jsonpickle.encode(self)

    @classmethod
    def from_dict(cls, data):
        return jsonpickle.decode(data)