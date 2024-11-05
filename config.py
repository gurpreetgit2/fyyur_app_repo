import os

SECRET_KEY = os.urandom(32)

# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode.
DEBUG = True

# Connect to the database
SQLALCHEMY_DATABASE_URI = 'postgresql://gurpreetatwal:abc@localhost:5432/fyyur'

# Additional configuration options
SQLALCHEMY_TRACK_MODIFICATIONS = False  # To suppress a warning

# Enable SQL query logging
SQLALCHEMY_ECHO = True
