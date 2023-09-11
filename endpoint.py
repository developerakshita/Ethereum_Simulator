import argparse
import logging
import os
import random
import socket
import threading
import time
from datetime import datetime

import jsonpickle
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request, abort

from beaconchain import BeaconChain
from block import Block
from state import State
from transaction import Transaction
from validator import Validator


class ValidatorNode:
    # Initialise the Beaconchain endpoints

    # local memory
    epoch = 0
    slot = 0
    localQueue = {}
    localBlockQueue = {}
    transaction_pool = {}
    block_pool = {}
    NeighborNodes = {}

    # Global set to keep track of processed transaction IDs
    processed_transaction_ids = set()
    processed_block_ids = set()

    # initialise a node

    ip_address = os.environ.get('IP_ADDRESS', '127.0.0.1')
    state_lock = threading.Lock()
    MAX_TRANSACTION_PER_BLOCK = 2
    beaconchain = {}

    def __init__(self, ip, port, stake, balance):
        self.ip_address = ip
        self.port = port
        self.stake = stake
        self.balance = balance
        self.node = Validator(balance, stake)
        self.eth_address = self.node.address
        self.app = Flask("validator")
        bootstrapper_ip = os.environ.get('BOOTSTRAPPER_IP', 'localhost')
        self.BOOTSTRAPPER_URL = f"http://{bootstrapper_ip}:5000"
        self.init_app()

    def init_app(self):
        self.app.add_url_rule('/', view_func=self.getNode, methods=['GET'])
        self.app.add_url_rule('/transact', view_func=self.transact, methods=['POST'])
        self.app.add_url_rule('/block-pool', view_func=self.process_block_queue, methods=['GET'])
        self.app.add_url_rule('/block-receive', view_func=self.blockReceive, methods=['POST'])
        self.app.add_url_rule('/show', view_func=self.show, methods=['GET'])
        self.app.add_url_rule('/transaction-receive', view_func=self.transactionReceive, methods=['POST'])
        self.app.add_url_rule('/ping', view_func=self.ping, methods=['GET'])
        self.app.add_url_rule('/set-role', view_func=self.set_role, methods=['POST'])
        self.app.add_url_rule('/block-proposer', view_func=self.block_proposer, methods=['GET'])
        self.app.add_url_rule('/update-vote', view_func=self.update_vote, methods=['POST'])
        self.app.add_url_rule('/update-beacon-chain', view_func=self.update_beacon_chain, methods=['POST'])
        self.app.add_url_rule('/epoch-updater', view_func=self.epoch_updater, methods=['GET'])
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=self.process_transaction_queue, trigger="interval", seconds=15)
        scheduler.add_job(func=self.process_block_queue, trigger="interval", seconds=15)
        scheduler.start()

    def process_block_queue(self):
        with self.beaconchain.locker:
            for block in self.localBlockQueue.values():
                for ip in self.NeighborNodes.values():
                    response = requests.post(f"http://{ip}/block-receive",
                                             json={"source": self.node.address,
                                                   "block": block.to_dict()})
                    if response.status_code == 200:
                        print(f"Block successfully received by {ip}")
            self.localBlockQueue.clear()
            return jsonify({"message": "Block successfully created and validated"}), 200

    def getNode(self):
        return jsonify({
            "eth_address": self.eth_address,
            "ip_address": self.ip_address,
            "balance": self.node.balance,
            "stake": self.node.stake,
            "state": self.node.state.to_dict(),
            "timestamp": time.time(),
            "neighborNodes": list(self.NeighborNodes.values())
        })

    def transact(self, transaction):
        transactionId = transaction.transactionId
        if transactionId is not None and transactionId in self.processed_transaction_ids:
            return jsonify({"message": "Transaction already processed"}), 200
        valid, msg = transaction.validate(self.node.state)

        if valid:
            self.node.state.nonces[transaction.sender] += 1
            self.node.state.balances[transaction.receiver] += transaction.amount
            self.node.state.balances[
                transaction.sender] -= transaction.amount + \
                                       (transaction.gas_price * transaction.gas_limit)

            transaction.state = self.node.state
            transaction.timestamp = int(time.time())

            self.localQueue[transactionId] = transaction
            self.transaction_pool[transactionId] = transaction
            self.processed_transaction_ids.add(transactionId)

            return jsonify({"message": "Transaction successfully created and validated"}), 200
        else:
            return jsonify({"message": msg}), 500

    def transact(self):
        try:
            with self.state_lock:
                data = request.json
                transactionId = data.get('transactionId')

                # Log the transaction receipt with timestamp
                logging.info(f"{datetime.now()} - Transaction received with ID: {transactionId}")

                if transactionId is not None and transactionId in self.processed_transaction_ids:
                    return jsonify({"message": "Transaction already processed"}), 200

                sender = data.get('sender')  # address
                amount = data.get('amount')
                private_key = data.get('private_key')
                receiver = data.get('receiver')  # address
                gas_price = data.get('gas_price')
                gas_limit = data.get('gas_limit')
                nonce = data.get('nonce')
                transaction = Transaction(sender, receiver, amount, nonce, gas_price, gas_limit)
                transaction.sign_transaction(private_key)

                valid, msg = transaction.validate(self.node.state)

                if valid:
                    self.node.state.nonces[sender] += 1
                    self.node.state.balances[receiver] += amount
                    self.node.state.balances[sender] -= amount + gas_price * gas_limit

                    transaction.state = self.node.state
                    transaction.timestamp = int(time.time())

                    self.localQueue[transaction.transactionId] = transaction
                    self.transaction_pool[transactionId] = transaction
                    self.processed_transaction_ids.add(transactionId)

                    return jsonify({"message": "Transaction successfully created and validated"}), 200
                else:
                    return jsonify({"message": msg}), 500
        except Exception as e:
            print(f"Error processing transaction: {e}")
            abort(500, description="Error processing transaction")

    def process_transaction_queue(self):
        self.getNeighbors()  # see if there are new nodes
        # FailedTransactions = []
        threads = []

        def broadcast_transaction(transaction, ip):
            response = requests.post(f"http://{ip}/transaction-receive",
                                     json={"source": self.node.address,
                                           "transaction": transaction.to_dict()})
            if response.status_code == 200:
                print(f"Transaction successfully received by {ip}")
            # else:
            #     print(f"Transaction failed to be received by {ip}")
            #     FailedTransactions.append(transaction)

        if len(list(self.localQueue.keys())) > 0:
            for transaction in self.localQueue.values():
                for ip in self.NeighborNodes.values():
                    thread = threading.Thread(target=broadcast_transaction, args=(transaction, ip,))
                    threads.append(thread)
                    thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        self.transaction_pool.update(self.localQueue)
        self.localQueue.clear()
        # for t in FailedTransactions:
        #     localQueue[t.transactionId] = t

    def blockReceive(self):
        start_time = datetime.now()
        with self.beaconchain.locker:
            # Log the receipt of the block with timestamp

            data = request.json
            # Setup logging configuration
            blockData = data.get('block')
            if not blockData:
                print("DEBUG: Block data missing from request")
                abort(400, description="Missing block data")

            block = Block.from_dict(blockData)
            logging.info(f"{start_time} - Block received with state root: {block.state_root}")
            print(f"DEBUG: Block after conversion: {jsonpickle.encode(block)}")

            if not block.state_root:
                print(f"DEBUG: Block {block.state_root} is not valid")
                return jsonify({"message": "Block ID is missing"}), 400

            if block.state_root in self.processed_block_ids:
                return jsonify({"message": "Block already processed"}), 200

            # check if this needs to be added to beaconchain here or a temporary queue

            parent_block = self.beaconchain.chain[-1]
            valid = self.beaconchain.add_block(block)
            if not valid:
                return jsonify({"message": "Block is not valid and cannot be added to beaconchain"}), 400

            # Add block to local queue
            self.localBlockQueue[block.state_root] = block
            if not parent_block.is_finalized:
                self.send_my_vote(parent_block, self.node.stake)
            print(f"DEBUG: I AM SENDING VOTE FOR BLOCK {block.state_root}")
            self.send_my_vote(block, self.node.stake)

        return jsonify({"message": "Block successfully received"}), 200

    def show(self):
        return jsonpickle.encode(self.beaconchain), 200

    def send_my_vote(self, block, stake):
        data = {
            "blockHash": block.state_root,
            "stake": stake,
            "epoch": block.epoch,
            "source": self.eth_address
        }
        print(f"Sending vote for block {block.state_root} to {self.BOOTSTRAPPER_URL}")

        url = f"{self.BOOTSTRAPPER_URL}/receive-vote"
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"Vote successfully received by {url}")
        else:
            print(f"Vote failed to be received by {url}")

    def transactionReceive(self):
        try:
            with self.state_lock:
                data = request.json

                transactionData = data.get('transaction')
                if not transactionData:
                    abort(400, description="Missing transaction data")

                transaction = Transaction.from_dict(transactionData)

                # Check if transaction ID exists and if transaction has already been processed
                if not transaction.transactionId:
                    return jsonify({"message": "Transaction ID is missing"}), 400
                if transaction.transactionId in self.processed_transaction_ids:
                    return jsonify({"message": "Transaction already processed"}), 200

                state = transaction.state
                self.node.state.nonces[transaction.sender] = state.nonces.get(transaction.sender, 0)
                self.node.state.balances[transaction.sender] = state.balances.get(transaction.sender, 0)

                self.node.state.nonces[transaction.receiver] = state.nonces.get(transaction.receiver, 0)
                self.node.state.balances[transaction.receiver] = state.balances.get(transaction.receiver, 0)

                self.localQueue[transaction.transactionId] = transaction

                return jsonify({"message": "Transaction successfully received"}), 200
        except (AttributeError, KeyError) as e:
            print(f"Error processing transaction data: {e}")
            abort(400, description="Invalid transaction data")
        except Exception as e:
            print(f"Error receiving transaction: {e}")
            abort(500, description="Error receiving transaction")

    def getNeighbors(self):
        response = requests.get(f"{self.BOOTSTRAPPER_URL}/get-nodes")
        if response.status_code == 200:
            data = response.json()  # Parse the JSON directly
            for node_info in data.values():  # Iterating through the nodes
                # Check if the current node is a neighbor of the node in the iteration
                if self.eth_address in node_info["neighborNodes"]:
                    # Add the node to the NeighborNodes dictionary
                    self.NeighborNodes[node_info["id"]] = node_info["ip"] + ":" + str(node_info["port"])
        else:
            print("Error getting neighbors")
            print("will retry later")

    def notify_bootstrapper(self, node_id, node_ip, port):
        payload = {
            "id": node_id,
            "ip": node_ip,
            "port": port,
            "stake": self.node.stake,
        }

        try:
            response = requests.post(self.BOOTSTRAPPER_URL + "/add-node", json=payload)
            if response.status_code == 200:
                self.node.state = State.from_dict(response.json().get('state'))
                self.beaconchain = BeaconChain.from_dict(response.json().get('beaconchain'))
                return True, response.json().get('message', '')
            else:
                return False, response.json().get('message', 'Unknown error')
        except requests.RequestException as e:
            return False, str(e)

    def ping(self):
        return jsonify({"message": "Node is alive"}), 200

    def set_role(self):
        role = request.json.get('role')
        epoch = request.json.get('epoch')
        slot = request.json.get('slot')
        validator_count = request.json.get('validator_count')
        print(f"DEBUG: Setting role to {role}")
        if role not in ['proposer', 'validator']:
            return jsonify({"message": "Invalid role"}), 400

        # Assuming the node object has a 'role' attribute
        self.node.role = role
        if role == 'proposer':
            with self.beaconchain.locker:
                num_samples = min(2, len(list(self.transaction_pool.keys())))
                randomTransactionKeys = random.sample(list(self.transaction_pool.keys()), num_samples)
                selectedTransactions = []
                if len(randomTransactionKeys) == 0:
                    return jsonify({"message": "No transactions available"}), 200
                for key in randomTransactionKeys:
                    selectedTransactions.append(self.transaction_pool[key])
                    del self.transaction_pool[key]
                start_time_bp_recieved = datetime.now()  # Capture the start time as soon as a request is received

                ProposedBlock = Block(self.beaconchain.chain[-1].index + 1, self.node,
                                      self.beaconchain.chain[-1].state_root,
                                      selectedTransactions)
                ProposedBlock.epoch = epoch
                ProposedBlock.slot = slot
                ProposedBlock.validator_count = validator_count
                ProposedBlock.justified_epoch_count = 0
                # Log the time taken to process and propose the block
                end_time_bp_recieved_time = datetime.now()
                duration = (end_time_bp_recieved_time - start_time_bp_recieved).total_seconds()
                logging.info(
                    f"{end_time_bp_recieved_time} - Block with state root {ProposedBlock.state_root} processed and proposed in {duration} seconds.")

                print(f"DEBUG: Proposing block with state root {ProposedBlock.state_root}")

                # ProposedBlock.sign(node.private_key)
                self.beaconchain.add_block(ProposedBlock)
                self.localBlockQueue[ProposedBlock.state_root] = ProposedBlock

                self.node.role = "validator"
                self.processed_block_ids.add(ProposedBlock.state_root)
        else:
            print("Do something for validators")
        return jsonify({"message": f"Role Set {role}"}), 200

    def block_proposer(self):
        with self.beaconchain.locker:
            return jsonify(
                {"message": "Block proposer", "block_proposed": jsonpickle.encode(self.beaconchain.chain)}), 200

    def update_vote(self):
        with self.beaconchain.locker:
            current_epoch = self.beaconchain.current_epoch
            data = request.json
            respond_with_data = []
            for obj in data:
                blockHash = obj.get('blockHash', None)
                votes = obj.get('vote_count')
                epoch = obj.get('epoch')
                if blockHash is None or blockHash in self.processed_block_ids:
                    continue
                for b in self.beaconchain.chain:
                    if b.state_root == blockHash:
                        b.set_votes(votes, current_epoch, epoch)
                        respond_with_data.append(
                            {
                                "blockHash": blockHash,
                                "justified": b.is_justified,
                                "finalized": b.is_finalized,
                                "epoch": epoch,
                                "vote_count": votes
                            })
                    if b.is_finalized:
                        self.processed_block_ids.add(blockHash)

            return jsonify(respond_with_data), 200

    def update_beacon_chain(self):
        with self.beaconchain.locker:
            data = request.json
            blockHash = data.get("blockHash")
            if blockHash in self.processed_block_ids:
                return jsonify({"message": "Block already processed"}), 200

            for b in self.beaconchain.chain:
                if b.state_root == blockHash:
                    b.is_justified = data.get("justified")
                    b.is_finalized = data.get("finalized")
                    break
        return jsonify({"message": "Beacon chain updated"}), 200

    def epoch_updater(self):
        with self.beaconchain.locker:
            self.beaconchain.current_epoch = request.args.get('epoch')
            return jsonify({"message": "Epoch updated"}), 200

    def flaskRunner(self):
        success, message = self.notify_bootstrapper(self.node.address, self.ip_address, self.port)
        print(message)
        if success:
            self.app.run(debug=False, host=self.ip_address, port=self.port)


def wait_for_bootstrapper(url):
    while True:
        try:
            response = requests.get(f'{url}/ping')
            if response.status_code == 200:
                print("Bootstrapper is up and running!")
                break
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to bootstrapper: {e}")

        # Wait for a few seconds before trying again
        time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Start the Flask app")
    parser.add_argument("--port", type=int, default=5001, help="Port to listen on")
    parser.add_argument("--stake", type=int, default=100, help="Stake of the node")
    parser.add_argument("--balance", type=int, default=1000, help="Balance of the node")
    args = parser.parse_args()
    container_ip = socket.gethostname()
    node = ValidatorNode(container_ip, args.port, args.stake, args.balance)
    wait_for_bootstrapper(node.BOOTSTRAPPER_URL)
    print("Node address: ", node.eth_address)
    ip_address = container_ip + ":" + str(args.port)
    node.flaskRunner()
