import hashlib

import jsonpickle


class MerkleNode:
    def __init__(self, hash_val, left=None, right=None):
        self.hash_val = hash_val
        self.left = left
        self.right = right

    def to_dict(self):
        return jsonpickle.encode(self)

    @classmethod
    def from_dict(cls, data):
        return jsonpickle.decode(data)


class MerkleTree:
    DEFAULT_EMPTY_ROOT = hashlib.sha256(b'').hexdigest()  # Default hash for an empty tree

    def __init__(self, transactions):
        self.transactions = transactions
        self.leaves = [MerkleNode(self.hash_data(tx)) for tx in transactions] if transactions else [
            MerkleNode(self.DEFAULT_EMPTY_ROOT)]
        self.root = self.build_tree(self.leaves)

    def hash_data(self, data):
        """Generate a sha256 hash for the given data."""
        return hashlib.sha256(data.encode()).hexdigest()

    def build_tree(self, leaves):
        """Build the Merkle tree and return the root node."""
        if len(leaves) == 1:
            return leaves[0]

        parent_nodes = []

        for i in range(0, len(leaves), 2):
            left = leaves[i]
            if i + 1 < len(leaves):
                right = leaves[i + 1]
                parent_hash = self.hash_data(left.hash_val + right.hash_val)
                parent_nodes.append(MerkleNode(parent_hash, left, right))
            else:
                parent_nodes.append(left)

        return self.build_tree(parent_nodes)

    def get_merkle_root(self):
        """Return the Merkle root hash."""
        return self.root.hash_val

    # For the MerkleTree class
    def to_dict(self):
        return jsonpickle.encode(self)

    @classmethod
    def from_dict(cls, data):
        return jsonpickle.decode(data)
