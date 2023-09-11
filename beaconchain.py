import jsonpickle
import time
import threading
PROPOSERS_COUNT = 3


class BeaconChain:
    locker = threading.Lock()
    def __init__(self, genesis_block):
        self.chain = [genesis_block]  # Starts empty since the genesis block is in the Block class
        self.current_epoch = 0
        # Justified block array to store blocks that have been justified but not finalized
        self.justified_blocks = []  # Changed from dictionary to list

    def validate_block(self, block):
        """Validate a block before adding to the chain."""
        # Ensure block continuity
        if self.chain:
            last_block = self.chain[-1]
            # if last_block.index + 1 != block.index:
            #     print(f"Invalid block due to index mismatch. Expected {last_block.index + 1}, got {block.index}.")

            #     return False
            if last_block.state_root != block.parent_hash:
                print(
                    f"Invalid block due to parent hash mismatch. Expected {last_block.state_root}, got {block.parent_hash}.")

                return False

        # Validate block's transactions
        if not block.validate_transactions():
            print(f"Invalid block due to transaction validation failure.")

            return False

        # Validate block's signature
        # if not block.verify_signature():
        #    return False

        return True

    def add_block(self, block):
        """Add a new block to the chain after validation."""

        # Validate the block first
        if not self.validate_block(block):
            print("Invalid block.")

        # If validation passes and no slashing condition met, append the block to the chain.
        self.chain.append(block)
        self.current_epoch=block.epoch
        
        return True


    def to_dict(self):
        return jsonpickle.encode(self)

    @classmethod
    def from_dict(cls, data):
        return jsonpickle.decode(data)

    def print_chain(self):
        print("Beacon Chain Blocks as Linked List:")
        for block in self.chain:
            print(f"Block Index: {block.index}, State Root: {block.state_root}, Parent Hash: {block.parent_hash}")
