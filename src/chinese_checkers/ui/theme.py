# zone                 # piece
RED = ["rgb(180,15,25)", "rgb(255,30,60)"]
PURPLE = ["rgb(135,10,185)", "rgb(190,0,250)"]
GREEN = ["rgb(10,155,10)", "rgb(5,200,5)"]
ORANGE = ["rgb(235,95,0)", "rgb(255,155,0)"]

COLORS = {
    "N": {"zone": RED[0], "piece": RED[1]},
    "NE": {"zone": "bright_black", "piece": "white"},
    "SE": {"zone": PURPLE[0], "piece": PURPLE[1]},
    "S": {"zone": GREEN[0], "piece": GREEN[1]},
    "SW": {"zone": "dodger_blue2", "piece": "dodger_blue1"},
    "NW": {"zone": ORANGE[0], "piece": ORANGE[1]},
    # FOR TESTING: PIECES IN THEIR GOAL ZONES
    # "N": {
    #     "zone": RED[0],
    #     "piece": GREEN[1]
    # },
    # "NE": {
    #     "zone": "bright_black",
    #     "piece": "dodger_blue1"
    # },
    # "SE": {
    #     "zone": PURPLE[0],
    #     "piece": ORANGE[1]
    # },
    # "S": {
    #     "zone": GREEN[0],
    #     "piece": RED[1]
    # },
    # "SW": {
    #     "zone": "dodger_blue2",
    #     "piece": "white"
    # },
    # "NW": {
    #     "zone": ORANGE[0],
    #     "piece": PURPLE[1]
    # }
}

CURSOR_PULSE_GREYS = [
    "grey23",
    "grey27",
    "grey30",
    "grey35",
    "grey39",
    "grey42",
    "grey46",
    "grey50",
    "grey54",
    "grey58",
    "grey62",
]
