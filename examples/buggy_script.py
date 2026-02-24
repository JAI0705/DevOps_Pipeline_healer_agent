# examples/buggy_script.py
# This file intentionally contains bugs for testing the Pipeline Healer Agent.

import os
import sys


def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    # BUG: Division by zero when the list is empty
    total = sum(numbers)
    return total / len(numbers)


def read_config(filepath):
    """Read a JSON config file."""
    import json

    # BUG: Missing error handling for file not found
    with open(filepath) as f:
        data = json.load(f)
    return data


def greet_users(users):
    """Print a greeting for each user."""
    for user in users:
        # BUG: KeyError if 'name' key doesn't exist
        print(f"Hello, {user['name']}! You are {user['age']} years old.")


def process_data(data):
    """Process and transform data."""
    results = []
    for item in data:
        # BUG: TypeError — mixing string concatenation with integer
        result = "Item: " + item + " processed at step " + 1
        results.append(result)
    return results


if __name__ == "__main__":
    # These calls will all fail
    print(calculate_average([]))
    print(read_config("nonexistent.json"))
    greet_users([{"username": "alice"}])
    process_data(["a", "b", "c"])
