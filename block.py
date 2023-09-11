import threading
import time

import jsonpickle
from ecdsa import SigningKey, SECP256k1

from merkle import MerkleTree


class Block:
    locker = threading.Lock()

    def __init__(self, index, proposer, parent_hash, transactions, state_root=None):
        self.index = index
        self.proposer = proposer
        self.parent_hash = parent_hash
        self.transactions = transactions
        self.is_justified = False
        self.is_finalized = False
        self.justified_epoch_count = 0
        self.slot = 0
        self.epoch = 0
        self.validator_count = 0
        self.block_votes_1 = 0
        self.block_votes_2 = 0
        self.created_time = time.time()
        self.updated_time = time.time()
        self.signature = None
        if state_root is not None:
            self.state_root = state_root
        else:
            self.state_root = self.generate_merkle_root()

    def serialize(self):
        """Serializing the block content for signing or signature verification."""
        return (str(self.index) + self.proposer.address + self.parent_hash +
                self.state_root + ''.join([tx.hash for tx in self.transactions]))

    def sign(self, private_key):
        """
        Signing the block using the given private key.

        Parameters:
        - private_key: The private key of the proposer to sign the block.
        """
        sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
        self.signature = sk.sign(self.serialize().encode())

    def verify_signature(self):
        """
        Verify the signature of the block using the proposer's public key.

        Returns:
        - True if the signature is valid, False otherwise.
        """

        # vk = VerifyingKey.from_string(bytes.fromhex(self.proposer.public_key[:]), curve=SECP256k1)
        # try:
        #     return vk.verify(self.signature, self.serialize().encode())
        # except:
        #     return False
        return True

    def get_transactions(self):
        """
        Retrieve the transactions in the block.

        Returns:
        - List of transactions in the block.
        """
        return self.transactions

    def validate_transactions(self):
        """for tx in self.transactions:
            is_valid, msg = tx.validate()  # Assuming validate() returns (is_valid, message)
            if not is_valid:
                print(f"Transaction validation failed: {msg}")
                return False
                """
        return True

    def generate_merkle_root(self):
        """Generate the Merkle root for the transactions in the block."""
        tree = MerkleTree([tx.serialize() for tx in self.transactions])
        return tree.get_merkle_root()

    def to_dict(self):
        return jsonpickle.encode(self)

    def check_validation_for_block(self):
        print("Checking if block is valid...")

        # Getting the total number of all validators
        total_validators_count = self.validator_count

        # If block_votes_1 has votes from more than 2/3 of the validators, justify the block
        if self.block_votes_1 > (2 / 3) * total_validators_count and not self.is_justified:
            self.is_justified = True
            self.justified_epoch = self.epoch 
            print(f"Block {self.index} is justified!")
            

        # If both block_votes_1 and block_votes_2 have votes from more than 2/3 of the validators, finalize the block
        if self.block_votes_2 > (2 / 3) * self.validator_count and self.is_justified and self.epoch == self.justified_epoch + 1:
            self.is_finalized = True
            print(f"Block {self.index} is finalized!")




    def set_votes(self, vote, current, epoch):
        with self.locker:
            self.epoch = epoch
            if not self.is_justified and self.epoch == current:
                self.block_votes_1 = vote
            else:
                self.block_votes_2 = vote

            self.check_validation_for_block()


    @classmethod
    def from_dict(cls, data):
        block = jsonpickle.decode(data)
        if block.state_root is None:
            block.state_root = block.generate_merkle_root()
        return block
