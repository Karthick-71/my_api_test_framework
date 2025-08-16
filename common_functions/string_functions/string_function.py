import random
import string
# import pandas as pd
from bson.objectid import ObjectId



def generate_random_string(no_of_digits):
    characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(no_of_digits))
    return random_string


def get_mongodb_object_id():
    """
    Generates a random MongoDB ObjectId.
    
    Returns:
        str: A string representation of the ObjectId.
    """
    # Generate a new ObjectId
    obj_id = ObjectId()

    return str(obj_id)