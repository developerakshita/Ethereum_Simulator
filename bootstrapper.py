import argparse
import threading
from collections import namedtuple
from random import uniform
from threading import Lock
import logging
import jsonpickle
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request

from beaconchain import BeaconChain
from block import Block
from state import State
from user import User
from validator import Validator

logging.basicConfig(filename='validator_selection.log', level=logging.INFO,format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
class BootStrapper:
    Voter = namedtuple('Voter', ['stake', 'validator'])

    def __init__(self, ip, port, balance=100, stake=0, MAX_SLOT=3):
        self.Nodes = {}
        self.lock = Lock()
        self.app = Flask("bootstrapper")
        self.init_app()
        self.MAX_SLOT = MAX_SLOT  # Initialize MAX_SLOT
        self.epoch = 0  # Initialize epoch
        self.slot = 0  # Initialize slot
        self.state = State({}, {})  
        self.node = Validator(balance, stake)
        self.slot_lock = threading.Lock()
        GENESIS_PARENT_HASH = "0" * 64  # 64 zeros for a 256-bit value in hex
        genesis_block = Block(0, self.node, GENESIS_PARENT_HASH, [])
        genesis_block.is_finalized = True
        genesis_block.proposer = self.node
        genesis_block.sign(self.node.private_key)
        self.block_vote = {}
        self.block_state_queue = {}
        self.ip = ip
        self.port = port
        self.beacon_chain = BeaconChain(genesis_block)

    def init_app(self):
        self.app.add_url_rule('/create-user', view_func=self.createUser, methods=['GET'])
        self.app.add_url_rule('/add-node', view_func=self.addNode, methods=['POST'])
        self.app.add_url_rule('/get-nodes', view_func=self.getNodes, methods=['GET'])
        self.app.add_url_rule('/add-neighbor', view_func=self.addNeighbor, methods=['POST'])
        self.app.add_url_rule('/receive-vote', view_func=self.receiveVote, methods=['POST'])
        self.app.add_url_rule('/ping', view_func=self.ping, methods=['GET'])

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(func=self.scheduled_task, trigger="interval", minutes=1)
        self.scheduler.add_job(func=self.vote_sender, trigger="interval", seconds=5)
        self.scheduler.add_job(func=self.block_updater, trigger="interval", seconds=10)
        self.scheduler.start()

    def createUser(self):
        
        user = User(state=self.node.state, balance=1000)
        self.state.balances[user.address] = user.balance
        self.state.nonces[user.address] = 0
        user.state = self.state
        return user.to_dict()

    def addNode(self):
        data = request.json
        node_id = data.get('id')
        node_ip = data.get('ip')
        port = data.get('port')
        stake = data.get('stake')

        # Check if node already exists
        if node_id in self.Nodes:
            return jsonify({"message": "Node already exists"}), 400

        # Add new node
        self.Nodes[node_id] = {
            "ip": node_ip,
            "id": node_id,
            "port": port,
            "neighborNodes": [],
            "visited": False,
            "stake": stake
        }
        return jsonify({"message": "Node added",
                        "state": self.state.to_dict(),
                        "beaconchain": self.beacon_chain.to_dict()}), 200

    def is_node_available(self, node_ip, port):
        try:
            response = requests.get(f"http://{node_ip}:{port}/ping", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def dfs(self, node, visited):
        subnetwork = []
        stack = [node]

        while stack:
            vertex = stack.pop()
            if vertex not in visited:
                visited.add(vertex)
                subnetwork.append(vertex)
                stack.extend(set(self.Nodes[vertex]["neighborNodes"]) - visited)

        return subnetwork

    def select_proposers(self, subnetwork):
        if len(subnetwork) < 2:
            return None
        available_nodes = subnetwork.copy()
        total_stake = sum([self.Nodes[node]["stake"] for node in available_nodes])
        random_choice = uniform(0, total_stake)
        current_sum = 0
        for node in available_nodes:
            current_sum += self.Nodes[node]["stake"]
            if current_sum >= random_choice:
                return node
        return available_nodes[0]

    def epoch_updater(self, epoch):
        with self.beacon_chain.locker():
            for node in self.Nodes.values():
                url = f"http://{node['ip']}:{node['port']}/epoch-updater"
                requests.get(url, params={'epoch': epoch})

    def scheduled_task(self):
        # Get the list of nodes that need to be checked
        nodes_to_check = list(self.Nodes.keys())

        # Create a list to store the available nodes
        available_nodes = []

        # Function to check node availability and update the result list
        def check_node_availability(n):
            if self.is_node_available(self.Nodes[n]["ip"], str(self.Nodes[n]["port"])):
                available_nodes.append(n)

        # Create threads for checking node availability
        threads = []
        for n in nodes_to_check:
            thread = threading.Thread(target=check_node_availability, args=(n,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        visited = set()
        subnetworks = []

        for node in available_nodes:
            if node not in visited:
                subnetwork = self.dfs(node, visited)
                subnetworks.append(subnetwork)

        for subnetwork in subnetworks:
            proposer = self.select_proposers(subnetwork)
            print(f"Selected proposers for subnetwork {subnetwork}: {proposer}")
            print("Proposer Value:", proposer)
            print("Proposer Type:", type(proposer))
            # Logging information to show which proposer is selected
            logging.info(f"Epoch: {self.epoch}, Slot: {self.slot}, Subnetwork: {subnetwork}, Selected proposer: {proposer}")
            if not proposer:
                continue
            self.set_node_role(self.Nodes[proposer], "proposer", self.epoch, self.slot, len(subnetwork) - 1)

        self.slot = self.slot + 1
        if self.slot == self.MAX_SLOT:
            self.epoch = self.epoch + 1
            self.slot = 0  # slot reset
            self.epoch_updater(self.epoch)

    def set_node_role(self, node, role, epoch, slot, validator_count):
        """
        Set the role for a node.

        Args:
        - ip (str): The IP address of the node.
        - port (int): The port number of the node.
        - role (str): The role to be set ('proposer' or 'validator').

        Returns:
        - str: Response message from the node.
        """
        ip = node["ip"]
        port = node["port"]
        # Define the endpoint URL based on the node's IP and port
        url = f"http://{ip}:{port}/set-role"

        # Define the payload to send to the endpoint
        data = {
            'role': role,
            'epoch': epoch,
            'slot': slot,
            'validator_count': validator_count
        }

        # Make the POST request and get the response
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json().get('message')
        except requests.RequestException as e:
            return str(e)

    def run(self):
        # creating two users
        user1 = bootstrapper.createUser()
        user2 = bootstrapper.createUser()
        user3 = bootstrapper.createUser()
        print(user1, "\n", user2, "\n", user3)
        self.app.run(debug=False, host=self.ip, port=self.port)

    def receiveVote(self):
        with self.beacon_chain.locker:
            data = request.json
            blockHash = data.get('blockHash')
            source = data.get('source')
            epoch = data.get('epoch')
            print(f"Received vote for block {blockHash} from {source}")

            if blockHash not in self.block_vote:
                self.block_vote[blockHash] = {"voters": set(), "epoch": epoch}
            self.block_vote[blockHash]["voters"].add(source)
            return jsonify({"message": "Vote received"}), 200

    def getNodes(self):
        return jsonpickle.encode(self.Nodes), 200

    def addNeighbor(self):
        data = request.json
        node_id_1 = data.get('node_id_1')
        node_id_2 = data.get('node_id_2')

        # Check if both nodes exist
        if node_id_1 not in self.Nodes or node_id_2 not in self.Nodes:
            return jsonify({"message": "One or both nodes don't exist."}), 400

        # Check if they are already neighbors
        if node_id_2 in self.Nodes[node_id_1]["neighborNodes"] or node_id_1 in self.Nodes[node_id_2]["neighborNodes"]:
            return jsonify({"message": "Nodes are already neighbors."}), 400

        # Add each node as a neighbor to the other
        self.Nodes[node_id_1]["neighborNodes"].append(node_id_2)
        self.Nodes[node_id_2]["neighborNodes"].append(node_id_1)

        return jsonify({"message": "Nodes set as neighbors successfully."}), 200

    def addNeighborns3(self, node_id_1, node_id_2):
        data = request.json

        # Check if both nodes exist
        if node_id_1 not in self.Nodes or node_id_2 not in self.Nodes:
            return jsonify({"message": "One or both nodes don't exist."}), 400

        # Check if they are already neighbors
        if node_id_2 in self.Nodes[node_id_1]["neighborNodes"] or node_id_1 in self.Nodes[node_id_2]["neighborNodes"]:
            return jsonify({"message": "Nodes are already neighbors."}), 400

        # Add each node as a neighbor to the other
        self.Nodes[node_id_1]["neighborNodes"].append(node_id_2)
        self.Nodes[node_id_2]["neighborNodes"].append(node_id_1)

        return jsonify({"message": "Nodes set as neighbors successfully."}), 200

    def vote_sender(self):
        with self.beacon_chain.locker:
            data = []
            for node in self.Nodes.values():
                url = f"http://{node['ip']}:{node['port']}/update-vote"
                for blockHash in list(self.block_vote.keys()):
                    obj = {
                        "blockHash": blockHash,
                        "vote_count": len(self.block_vote[blockHash]["voters"]),
                        "epoch": self.block_vote[blockHash]["epoch"],
                    }
                    data.append(obj)
                    print(f"Sending vote for block {blockHash} to {node['ip']}:{node['port']}")
                try:
                    response = requests.post(url, json=data)
                    response.raise_for_status()

                    for obj in response.json():
                        if self.block_state_queue.get(obj["blockHash"]) is None:
                            self.block_state_queue[obj["blockHash"]] = obj
                        else:
                            existing = self.block_state_queue[obj["blockHash"]]
                            existing["justified"] = obj["justified"] or existing["justified"]
                            existing["finalized"] = obj["finalized"] or existing["finalized"]
                except requests.RequestException as e:
                    print("vote sending failed")

    def block_updater(self):
        with self.beacon_chain.locker:
            for blockHash in list(self.block_state_queue.keys()):
                obj = self.block_state_queue[blockHash]

                for node in self.Nodes.values():
                    url = f"http://{node['ip']}:{node['port']}/update-beacon-chain"
                    try:
                        response = requests.post(url, json=obj)
                        response.raise_for_status()
                    except requests.RequestException as e:
                        print(f"block updating failed: {e}")

                if obj["finalized"]:
                    del self.block_vote[blockHash]
                    print("Block finalized")

    def removeVote(self):
        blockHash = request.args.get('blockHash')
        del self.block_vote[blockHash]

    def receiveVote(self):
        data = request.json
        blockHash = data.get('blockHash')
        source = data.get('source')
        epoch = data.get('epoch')
        print(f"Received vote for block {blockHash} from {source}")

        if blockHash not in self.block_vote:
            self.block_vote[blockHash] = {"voters": set(), "epoch": epoch}
        self.block_vote[blockHash]["voters"].add(source)
        return jsonify({"message": "Vote received"}), 200

    def ping(self):
        return jsonify({"message": "Node is alive"}), 200


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Start the Flask app")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="IP address to listen on")
    parser.add_argument("--balance", type=str, default=1000, help="Node Balance")
    parser.add_argument("--stake", type=str, default=60, help="Node Stake")
    parser.add_argument("--max_slots", type=str, default=3, help="Max Slots")
    args = parser.parse_args()
    bootstrapper = BootStrapper(args.ip, args.port, args.balance, args.stake, args.max_slots)
    bootstrapper.run()
