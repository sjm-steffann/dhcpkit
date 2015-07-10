import os


def create_transaction_id():
    return os.urandom(3)
