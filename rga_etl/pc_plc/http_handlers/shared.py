INIT_COMMANDS = [
    {"main": "ID?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "IN0\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "FL1.0\r", "length": 128, "noresult": 0, "timeout": 10.0},
]

END_COMMANDS = [
    {"main": "MR0\r", "length": 128, "noresult": 1, "timeout": 1.0},
    {"main": "FL0.0\r", "length": 128, "noresult": 0, "timeout": 10.0},
]
