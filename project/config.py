from enum import Enum

server_name = "US-east"
discord_hook_key = ""
role_to_ping = 123
resource_key = "123abc"

history_tags_metadata = [
    {
        "name": "status",
        "description": "Operating info about the api and filler.",
    },
    {
        "name": "stations",
        "description": "Query info about stations. (by default for the last 24 hrs)",
    },
    {
        "name": "railroaders",
        "description": "Query info about railroaders. (by default for the last 24 hrs unless you set a 'after' param)",
    },
    {
        "name": "admin",
        "description": "admin dash + raw logrun and usefuel actions from local db",
    },
    {
        "name": "atomic",
        "description": "local copy of atomicassets data for templates and assets",
    },
]

achv_tags_metadata = [
    {
        "name": "status",
        "description": "Operating info about the api.",
    },
    {
        "name": "achievements",
        "description": "Query info about avs. ",
    },
    
]

class FuelType(str, Enum):
    COAL = "COAL"
    DIESEL = "DIESEL"

class OrderChoose(str, Enum):
    desc = "desc"
    asc = "asc"

wanted_actions = ["logrun","logtips","npcencounter"]
wanted_templates = ["passengercar","passenger","locomotive","conductor","railcar","commodity","station"]
