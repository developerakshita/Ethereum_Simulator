import random
import time
from beaconchain import BeaconChain
from block import Block
from transaction import Transaction
from user import User
from validator import Validator
from state import State

# Initial parameters-> number of users, validators, epochs, blocks per epoch, and transactions per block
NUM_USERS = 10
NUM_VALIDATORS = 4
EPOCHS = 3
BLOCKS_PER_EPOCH = 4
TRANSACTIONS_PER_BLOCK = 5
# Define a constant for the genesis block's parent hash
GENESIS_PARENT_HASH = "0" * 64  # 64 zeros for a 256-bit value in hex

# Initialization of users, validators and beacon chain
blockchain_state = State()
validators = [Validator(100,10) for _ in range(NUM_VALIDATORS)]
genesis_block = Block(0, None, GENESIS_PARENT_HASH, "0" * 64, [])
beacon_chain = BeaconChain(validators, genesis_block, blockchain_state)
users = [User(beacon_chain.state,10000) for _ in range(NUM_USERS)]

# Simulating transactions
transaction_queue = []
for _ in range(EPOCHS * BLOCKS_PER_EPOCH * TRANSACTIONS_PER_BLOCK):
    sender = random.choice(users)
    receiver = random.choice(users)
    while receiver == sender:  # Ensure the receiver is not the same as the sender
        receiver = random.choice(users)
    amount = random.randint(1, 10)  # Random amount between 1 and 10
    tx = sender.send_transaction(receiver, amount)
    if tx:
        #print(f"Transaction from {tx.sender.address} to {tx.receiver.address} for {tx.amount} with nonce {tx.nonce}")

        transaction_queue.append(tx)

# Simulating block proposal, voting, and addition
for epoch in range(EPOCHS):
    for _ in range(BLOCKS_PER_EPOCH):
        # Select a proposer
        proposer = random.choice(beacon_chain.active_proposers)
        
        # Propose a block
        transactions_for_block = [transaction_queue.pop() for _ in range(TRANSACTIONS_PER_BLOCK) if transaction_queue]
        previous_block = beacon_chain.chain[-1]
        block = Block(len(beacon_chain.chain), proposer, previous_block.state_root, previous_block.state_root, transactions_for_block)
        
        # Add block to the beacon chain
        block_is_valid = beacon_chain.add_block(block)

        #If block is not valid, add transactions back to the mempool
        if not block_is_valid:
            for tx in block.transactions:
                transaction_queue.append(tx)

        
        # Validators vote on the block
        #In real life scenario, validators may not vote for a block due to network issues, or other reasons
        votes = 0
        for validator in validators:
            if random.random() < 0.8:  # 80% chance a validator votes for the block
                beacon_chain.vote_for_block(block, validator)
                votes += 1
        
        # If block receives more than 2/3 of total votes, it's added to justified_blocks
        if votes > (2/3) * len(validators):
            #Ensure block is not already in justified_blocks with a specific epoch
            if (block, beacon_chain.current_epoch) not in beacon_chain.justified_blocks:
                 beacon_chain.justified_blocks.append((block, beacon_chain.current_epoch))

    # End of epoch logic
    beacon_chain.epoch_transition()

# Finalization of blocks that have been justified for two epochs
for block, block_epoch in beacon_chain.justified_blocks:
    if block_epoch == beacon_chain.current_epoch - 2:
        beacon_chain.chain.append(block)
        beacon_chain.justified_blocks.remove((block, block_epoch))

# Display the state of the beacon chain
for block in beacon_chain.chain:
    print(f"Block Index: {block.index}, Proposed by: {block.proposer}, Number of Transactions: {len(block.transactions)}, Is finalized: {'Yes' if block in beacon_chain.chain else 'No'}")

