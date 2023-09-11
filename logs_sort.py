import re
from collections import defaultdict

# Sample log line format: 'ethereum_simulation-validator-3     | 2023-09-03T19:50:41.733319000Z Block successfully received by e7e5f046bbfd:5001'
#log_line_pattern = r"ethereum_simulation-validator-([1-7])\s+\|\s+(?P<timestamp>[\d:TZ.-]+)\s+(?P<message>.+)"
log_line_pattern = r"eth20_pos-validator-([1-7])\s+\|\s+(?P<timestamp>[\d:TZ.-]+)\s+(?P<message>.+)"
unique_messages = [
    r"Transaction received with ID: (.+)",
    r"Transaction successfully received by (.+)",
    r"DEBUG: Setting role to (.+)",
    r"DEBUG: Proposing block with state root (.+)",
    r"Block successfully received by (.+)",
    r"\"message\": \"Block successfully created and validated\"",
    r"DEBUG: Block data missing from request",
    r"DEBUG: I AM SENDING VOTE FOR BLOCK (.+)",
    r"Sending vote for block (.+) to (.+)",
    r"Vote successfully received by (.+)"
    # r"DEBUG: Proposing block with state root (.+)",
    # r"Block (.+) is justified!"
]

# Initialize a nested dictionary to store the earliest timestamp for each unique message
earliest_timestamps_by_validator = defaultdict(lambda: defaultdict(str))

with open("logs2", "r") as f:
    for line in f:
        match = re.search(log_line_pattern, line)
        if match:
            validator_number = match.group(1)
            timestamp = match.group("timestamp")
            message = match.group("message")
            for unique_message in unique_messages:
                unique_match = re.match(unique_message, message)
                if unique_match:
                    captured_groups = unique_match.groups()
                    if captured_groups:
                        message_key = f"{message}"
                    else:
                        message_key = unique_message
                    if not earliest_timestamps_by_validator[validator_number].get(message_key) or \
                            timestamp < earliest_timestamps_by_validator[validator_number][message_key]:
                        earliest_timestamps_by_validator[validator_number][message_key] = timestamp
                    break

# Write the collected earliest timestamps to a text file
with open("final_lifecycle2.txt", "w") as f_out:
    for validator in sorted(earliest_timestamps_by_validator.keys(), key=int):
        f_out.write(f"Validator {validator}:\n")
        messages = earliest_timestamps_by_validator[validator]
        for message, timestamp in messages.items():
            f_out.write(f"  Message: {message}\n")
            f_out.write(f"  Earliest Timestamp: {timestamp}\n")
