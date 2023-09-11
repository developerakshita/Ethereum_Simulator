import sha3
from ecdsa import SigningKey, SECP256k1

from state import State
from transaction import Transaction
def generate_keypair():
    private_key = SigningKey.generate(curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    private_key_hex = private_key.to_string().hex()

    # Convert the public key to bytes and derive Ethereum address from it
    pubkey_bytes = public_key.to_string()
    address = '0x' + sha3.keccak_256(pubkey_bytes).digest()[-20:].hex()

    public_key_hex = "0x" + public_key.to_string().hex()  # Store public key as hex
    return private_key_hex, public_key_hex, address