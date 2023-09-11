import logging

import jsonpickle

import util
from state import State


class Validator():
    """A class representing a Validator in the beacon chain."""

    def __init__(self, balance, stake):
        """
        Initialize a new Validator.

        Parameters:
        - stake: Amount of currency the validator has staked.
        """
        self.balance = balance
        self.state = State({}, {})
        self.private_key, self.public_key, self.address = util.generate_keypair()
        self.stake = stake
        self.blocks_validated = []  # List to store blocks validated by this validator
        self.blocks_proposed = []  # List to store blocks proposed by this validator
        self.rewards = 0  # Total rewards earned by the validator

    def propose_block(self, index, parent_hash, transactions=[]):
        from block import Block
        """Propose a new block to be added to the beacon chain."""
        new_block = Block(index, self, parent_hash, transactions)
        new_block.sign(self.private_key)  # Sign the proposed block
        self.blocks_proposed.append(new_block)
        return new_block

    def validate_block(self, block):
        """Validate the provided block."""
        # Verify the block's signature
        if not block.verify_signature():
            return False

        # Check the parent hash for continuity
        last_block = self.blocks_proposed[-1] if self.blocks_proposed else None
        if last_block and last_block.state_root != block.parent_hash:
            return False

        # Verify transactions in the block
        for tx in block.transactions:
            valid, _ = tx.validate()
            if not valid:
                return False

        # Recreate the Merkle root from the block's transactions and compare with the block's state root
        reconstructed_merkle_root = block.generate_merkle_root()
        if block.state_root != reconstructed_merkle_root:
            return False

        # Checking the block was proposed by a legitimate validator
        if block.proposer not in self.blocks_proposed:  # For simplicity, we're just checking against the blocks this validator proposed.
            return False

        return True

    def receive_reward(self, amount):
        """Credit the validator with the provided reward."""
        self.rewards += amount
        self.balance += amount  # Add the reward to the validator's balance

    def increase_stake(self, amount):
        """Increase the validator's stake by the provided amount."""
        if self.balance < amount:
            logging.warning("Insufficient balance to stake.")
            return
        self.balance -= amount
        self.stake += amount

    def decrease_stake(self, amount):
        """Decrease the validator's stake by the provided amount."""
        if self.stake < amount:
            logging.warning("Stake is less than the desired amount to unstake.")
            return
        self.stake -= amount
        self.balance += amount

    def to_dict(self):
        return jsonpickle.encode(self)

    @classmethod
    def from_dict(cls, data):
        return jsonpickle.decode(data)

