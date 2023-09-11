# Ethereum 2.0 PoS Simulation (Partial Gasper Implementation)

## Table of Contents
- [Introduction](#introduction)
- [Setup and Installation](#setup-and-installation)
- [Components](#components)
  - [Docker Services](#docker-services)
  - [Python Modules](#python-modules)
- [Transaction Lifecycle](#transaction-lifecycle)
- [Block Proposal](#block-proposal)
- [Validators and Attestations](#validators-and-attestations)
- [Finality](#finality)
- [Time Management](#time-management)
- [Classes](#classes)
  - [Validator](#validator)
  - [Endpoints](#endpoints)
  - [User](#user)
  - [MerkleNode](#merklenode)
  - [MerkleTree](#merkletree)
  - [Transaction](#transaction)
  - [State](#state)
  - [BeaconChain](#beaconchain)
  - [Block](#block)
- [API Endpoints](#api-endpoints)
- [Utility Functions](#utility-functions)
- [Future Scope](#future-scope)
- [GitIgnore](#gitignore)
- [License](#license)

## Introduction

This repository contains a partial simulation model of Ethereum 2.0's Proof-of-Stake (PoS) network, specifically focusing on the block voting aspect of the Gasper consensus mechanism. Gasper is a combination of the Casper Friendly Finality Gadget (Casper-FFG) and the LMD-GHOST fork choice rule. This simulation aims to explore how validators vote for blocks and how these votes contribute to block acceptance or rejection in the network.


## Setup and Installation


### Prerequisites

- Docker 19.03 or higher
- Docker-Compose 3.0 or higher

### Build and Run
To build and run the project, navigate to the root directory and execute:


'''bash
git clone <repository_link>
cd eth2.0_pos
pip install -r requirements.txt
docker-compose up --build
'''

## Components
### Docker Services
<!--Docker Services Content-->

- **Bootstrapper**: The entry node that initializes the network.
  - Port: 5000
  - Environment Variables: SERVICE_NAME=bootstrapper
- **Validator Nodes**: Validators responsible for proposing and attesting blocks.
  - Port Range: 5001-5008
  - Depends On: Bootstrapper
  - Environment Variables: BOOTSTRAPPER_IP=bootstrapper

### Python Modules
<!-- Python Modules content -->

- `beaconchain.py`: Manages the Beacon Chain.
- `block.py`: Defines Ethereum block structure and related logic.
- `bootstrapper.py`: The main server responsible for bootnode.
- `endpoint.py`: Represents a network endpoint, which acts as a validator 
- `transaction.py`: Manages transaction creation, signing, and verification.
- `validator.py`: Defines the logic related to Ethereum 2.0 validators.
- `state.py`: Manages the state of Ethereum, like accounts, contracts, etc.
- `util.py`: Utility functions used across the project.


- Transaction Creation: A user creates and signs a transaction. The gas for transaction processing is set by the user. (See: `transaction.py`)
- Transaction Validation: The submitted transaction is validated by the receiving Ethereum node.
- Transaction Pool: Valid transactions are stored in a mempool.
- Transaction Inclusion: The block proposer for the current slot includes transactions from the mempool into a new block.

## Block Proposal

- Proposer Selection: A validator is pseudo-randomly chosen to propose a new block. (See: `select_proposers` function)
- Block Creation: The chosen validator creates a new block containing transactions from the mempool.
- Block Broadcast: The new block is broadcasted to all validators.

## Validators and Attestations

- Receipt of Block: Validators receive the new block and validate it. (See: `blockReceive` function)
- Voting: Validators cast their votes for the received block. These votes are aggregated and stored in the Beacon Chain. (See: `vote_sender` function)

## Finality

- A block reaches finality when it receives a supermajority link, which is 66% of the total staked ETH in the network, between two epoch checkpoints.


## Time Management

- Slot Duration: 1 minute
- Epoch Duration: 3 minutes


## Classes


### Validators

Represents a Validator in the beacon chain.

#### Attributes:

- `balance`: The balance held by the validator.
- `state`: The state of the validator, an instance of the `State` class.
- `private_key`, `public_key`, `address`: Key-pair details and address of the validator.
- `stake`: Amount of currency the validator has staked.
- `rewards`: Total rewards earned by the validator.

#### Methods:

- `propose_block(index, parent_hash, transactions=[])`: Proposes a new block to be added to the beacon chain.
- `validate_block(block)`: Validates the provided block.


### Endpoints
Represents a validator with an Ethereum address.

#### Methods:

- `set_role`
- `update_vote`
- `UPDATE_VOTE`
- `update_beacon_chain`
- `epoch_updater`
- `transact`
- `send_my_vote`
- `blockReceive`

#### Functions in endpoint.py

- `send_my_vote(block, stake)`: Sends votes for a block.
- `block_updater()`: Updates blocks and manages finalized blocks.
- `removeVote()`: Removes votes for a block.


### User
Represents a user with an Ethereum address and private key.

#### Attributes:

- `state`: The state associated with the user.
- `private_key`, `public_key`, `address`: Key-pair details and address of the user.
- `balance`: The balance held by the user.
- `transaction_history`: List storing all transactions initiated by the user.
- `nonce`: Track the number of transactions sent by the user.

#### Methods:

- `send_transaction(receiver, amount)`: Sends a transaction from this user to a receiver.

### MerkleNode
Represents a node in a Merkle tree.

#### Attributes:

- `hash_val`: The hash value associated with the node.
- `left`: Left child of the node.
- `right`: Right child of the node.

#### Methods:

- `to_dict()`: Converts the object to a dictionary.
- `from_dict(data)`: Creates an instance from a dictionary.



### MerkleTree
Represents a Merkle tree.

#### Attributes:

- `transactions`: List of transactions in the Merkle tree.
- `leaves`: List of leaf nodes in the Merkle tree.
- `root`: Root node of the Merkle tree.

#### Methods:

- `hash_data(data)`: Generates a sha256 hash for the given data.
- `build_tree(leaves)`: Builds the Merkle tree and returns the root node.
- `get_merkle_root()`: Returns the Merkle root hash.
- `to_dict()`: Converts the object to a dictionary.
- `from_dict(data)`: Creates an instance from a dictionary.

### Transaction
Represents a transaction in the Ethereum network.

#### Attributes:

- `sender`: Sender's address.
- `receiver`: Receiver's address.
- `amount`: Amount to be transferred.
- `nonce`: Nonce associated with the transaction.
- `signature`: Transaction's signature.

#### Methods:

- `sign(private_key)`: Sign the transaction with the sender's private key.
- `verify_signature()`: Verify the transaction's signature.
- `is_valid()`: Check if the transaction is valid.
- `to_dict()`: Convert the transaction to a dictionary.
- `from_dict(data)`: Create a transaction instance from a dictionary.



### State
Manages all the account balances and nonces.

#### Attributes:

- `balances`: Dictionary storing account balances. Key: Address, Value: Balance.
- `nonces`: Dictionary storing account nonces. Key: Address, Value: Nonce.

#### Methods:

- `to_dict()`: Convert the state to a dictionary.
- `from_dict(data)`: Create a state instance from a dictionary.
- `get_balance(address)`: Retrieve the balance for an address.
- `set_balance(address, amount)`: Set the balance for an address.
- `get_nonce(address)`: Retrieve the nonce for an address.
- `set_nonce(address, nonce)`: Set the nonce for an address.
- `process_transaction(transaction)`: Process a transaction and update the state.


### Block
Represents a block in the beacon chain.

#### Attributes:

- `index`: The index of the block.
- `parent_hash`: Hash of the parent block.
- `transactions`: List of transactions in the block.

#### Methods:

- `add_transaction(transaction)`: Adds a transaction to the block.
- `retrieve_transactions()`: Retrieves transactions in the block.
- `validate_transactions()`: Validates all transactions in the block.
- `generate_merkle_root()`: Generates the Merkle root of the block's transactions.
- `check_validation_for_block()`: Checks if the block is valid based on voting.
- `set_votes(vote, current, epoch)`: Sets votes for the block and checks its validation.



### BeaconChain
<!-- <!-Need to write!> -->
Represents the beacon chain in Ethereum 2.0.

**Attributes**:
- `chain`: List that holds the blocks in the beacon chain.
- `current_epoch`: The current epoch of the beacon chain.



## Utility Functions

### generate_keypair()

Generates a key pair (private and public keys) and derives an Ethereum address from the public key.

#### Returns:

- `private_key_hex`: Hex representation of the private key.
- `public_key_hex`: Hex representation of the public key.
- `address`: Ethereum address derived from the public key.


- `build_tree(leaves)`: Builds the Merkle tree and returns the root node.
- `get_merkle_root()`: Returns the Merkle root hash.
- `to_dict()`: Converts the object to a dictionary.
- `from_dict(data)`: Creates an instance from a dictionary.

## API Endpoints

### From endpoint.py

#### Receive Vote

**Endpoint**: `/receive-vote`
**Method**: GET
**Parameters**:
- `blockHash`: The hash of the block.
- `source`: Source of the vote.
- `epoch`: Current epoch.

#### Description:

Receives votes for a block.

#### Response:

A JSON message confirming the receipt of the vote.

### Get Node Details

**Endpoint**: `/`

**Method**: GET

**Description**: Returns details about the node.

### Transact

**Endpoint**: `/transact`

**Method**: POST

**Description**: Handles transactions, ensuring they are valid and processes them.


### Functions in bootstrapper.py

#### epoch_updater(epoch)

Updates the epoch for nodes.

#### scheduled_task()

Periodically checks node availability, selects proposers for subnetworks, manages slots, and epochs.

#### set_node_role(node, role, epoch, slot, validator_count)

Sets the role for a node (either 'proposer' or 'validator').

## Future Scope


- Sharding: To increase scalability by allowing parallel transaction processing.
- BLS Signature: For better key management in PoS.
- Aggregators in Attestation: To reduce the overhead associated with transmitting individual votes.



## GitIgnore


## License

