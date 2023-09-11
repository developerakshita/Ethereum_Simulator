import requests

# The base URL for the Bootstrapper API
base_url = "http://localhost:5000"

# Ask the user for required information
sender_address = input("Enter the sender's address (User 1): ")
receiver_address = input("Enter the receiver's address (User 2): ")
sender_private_key = input("Enter the sender's private key: ")
endpoint_port = input("enter the port of endpoint `docker ps` to see the port:")

# Endpoint URL for the transaction
ENDPOINT_URL = f"http://127.0.0.1:{endpoint_port}/transact"

# Sample transaction data
transaction_template = {
    "sender": sender_address,
    "receiver": receiver_address,
    "amount": 10,  # Static amount for each transaction
    "gas_price": 0.5,  # Static gas price
    "gas_limit": 1,  # Static gas limit
    "private_key": sender_private_key
}


def create_neighbor_pairs():
    # The endpoint for getting nodes
    get_nodes_endpoint = "/get-nodes"

    # The endpoint for adding neighbors
    add_neighbor_endpoint = "/add-neighbor"

    # Fetch the current nodes
    response = requests.get(f"{base_url}{get_nodes_endpoint}")
    if response.status_code != 200:
        print("Failed to fetch nodes.")
        return

    # Extract the node IDs
    node_data = response.json()
    node_ids = list(node_data.keys())

    # Validate the number of nodes
    if len(node_ids) < 7:
        print("Not enough nodes to create neighbor pairs.")
        return

    # Pairs to be created as neighbors
    pairs = [(1, 3), (2, 3), (3, 4), (4, 5), (5, 6), (5, 7)]

    # Create the neighbor pairs
    for pair in pairs:
        id1 = node_ids[pair[0] - 1]
        id2 = node_ids[pair[1] - 1]

        payload = {
            "node_id_1": id1,
            "node_id_2": id2
        }

        response = requests.post(f"{base_url}{add_neighbor_endpoint}", json=payload)

        if response.status_code == 200:
            print(f"Successfully added neighbor pair: {id1}, {id2}")
        else:
            print(f"Failed to add neighbor pair: {id1}, {id2}")


def send_transaction(nonce):
    """Send a single transaction with the specified nonce."""
    transaction = transaction_template.copy()
    transaction["nonce"] = nonce
    response = requests.post(ENDPOINT_URL, json=transaction)
    print(f"Transaction with nonce {nonce}:", response.json())

if __name__ == "__main__":
    create_neighbor_pairs()
    for nonce in range(1, 10):
        send_transaction(nonce)
