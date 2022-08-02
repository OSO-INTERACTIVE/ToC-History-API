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


wanted_actions = ["logrun", "logtips", "npcencounter"]
wanted_templates = ["passengercar", "passenger", "locomotive", "conductor", "railcar", "commodity", "station"]

achv_mapped = {
    "Beta Badge": 1,
    "Golden Railroader": 2,
    "Golden Runner": 3,
    "Centuryville Connoisseur": 4,
    "T Pines Traveler": 5,
    "Pemberton Nights": 6,
    "James Park Juggalo": 7,
    "Paw Paw Pro": 8,
    "Modern Master": 9,
    "Otto’s Fellow 1": 10,
    "Otto’s Colleague 2": 11,
    "Otto’s Companion 3": 12,
    "Otto’s Enemy 4": 13,
    "Otto's Bro 5": 14,
    "7 Day Streak 1": 15,
    "30 Day Streak 2": 16,
    "90 Day Streak 3": 17,
    "180 Day Streak 4": 18,
    "365 Day Streak 5": 19,
    "Train Maestro": 20,
    "Full Train": 21,
    "Pallet Pusher 1": 22,
    "Pallet Pusher 2": 23,
    "Pallet Pusher 3": 24,
    "Pallet Pusher 4": 25,
    "Pallet Pusher 5": 26,
    "Crate Carrier 1": 27,
    "Crate Carrier 2": 28,
    "Crate Carrier 3": 29,
    "Crate Carrier 4": 30,
    "Crate Carrier 5": 31,
    "Liquid Lifter 1": 32,
    "Liquid Lifter 2": 33,
    "Liquid Lifter 3": 34,
    "Liquid Lifter 4": 35,
    "Liquid Lifter 5": 36,
    "Mr. Gas 1": 37,
    "Mr. Gas 2": 38,
    "Mr. Gas 3": 39,
    "Mr. Gas 4": 40,
    "Mr. Gas 5": 41,
    "Woodchip King 1": 42,
    "Woodchip King 2": 43,
    "Woodchip King 3": 44,
    "Woodchip King 4": 45,
    "Woodchip King 5": 46,
    "Rock Hustler 1": 47,
    "Rock Hustler 2": 48,
    "Rock Hustler 3": 49,
    "Rock Hustler 4": 50,
    "Rock Hustler 5": 51,
    "Sugar Daddy 1": 52,
    "Sugar Daddy 2": 53,
    "Sugar Daddy 3": 54,
    "Sugar Daddy 4": 55,
    "Sugar Daddy 5": 56,
    "Grainasaurus Rex 1": 57,
    "Grainasaurus Rex 2": 58,
    "Grainasaurus Rex 3": 59,
    "Grainasaurus Rex 4": 60,
    "Grainasaurus Rex 5": 61,
    "Icicle Jones 1": 62,
    "Icicle Jones 2": 63,
    "Icicle Jones 3": 64,
    "Icicle Jones 4": 65,
    "Icicle Jones 5": 66,
    "Big Shit Express 1": 67,
    "Big Shit Express 2": 68,
    "Big Shit Express 3": 69,
    "Big Shit Express 4": 70,
    "Big Shit Express 5": 71,
    "Rob the Builder 1": 72,
    "Rob the Builder 2": 73,
    "Rob the Builder 3": 74,
    "Rob the Builder 4": 75,
    "Rob the Builder 5": 76,
    "OttoMobile 1": 77,
    "OttoMobile 2": 78,
    "OttoMobile 3": 79,
    "OttoMobile 4": 80,
    "OttoMobile 5": 81,
    "Entity 9’s BFF 1": 82,
    "Entity 9’s BFF 2": 83,
    "Entity 9’s BFF 3": 84,
    "Entity 9’s BFF 4": 85,
    "Entity 9’s BFF 5": 86,
}
