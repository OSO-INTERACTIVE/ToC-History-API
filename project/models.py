from typing import Optional, List
from sqlalchemy import Column, String, Integer
from sqlmodel import SQLModel, Field, Relationship


class LogrunCarLink(SQLModel, table=True):
    logrun_id: Optional[int] = Field(
        default=None, foreign_key="logrun.id", primary_key=True, nullable=False
    )
    car_id: Optional[int] = Field(
        default=None, foreign_key="car.id", primary_key=True, nullable=False
    )
class CarLoadLink(SQLModel, table=True):
    asset_id: Optional[str] = Field(
        default=None, foreign_key="asset.asset_id", primary_key=True, nullable=False
    )
    car_id: Optional[int] = Field(
        default=None, foreign_key="car.id", primary_key=True, nullable=False
    )
class CarRailcarLink(SQLModel, table=True):
    asset_id: Optional[str] = Field(
        default=None, foreign_key="asset.asset_id", primary_key=True, nullable=False
    )
    car_id: Optional[int] = Field(
        default=None, foreign_key="car.id", primary_key=True, nullable=False
    )    
class LogrunConductorLink(SQLModel, table=True):
    asset_id: Optional[str] = Field(
        default=None, foreign_key="asset.asset_id", primary_key=True, nullable=False
    )
    logrun_id: Optional[int] = Field(
        default=None, foreign_key="logrun.id", primary_key=True, nullable=False
    )   
class LogrunLocomotiveLink(SQLModel, table=True):
    asset_id: Optional[str] = Field(
        default=None, foreign_key="asset.asset_id", primary_key=True, nullable=False
    )
    logrun_id: Optional[int] = Field(
        default=None, foreign_key="logrun.id", primary_key=True, nullable=False
    )   
class LogrunTipsLink(SQLModel, table=True):
    logtips_id: Optional[int] = Field(
        default=None, foreign_key="logtip.id", primary_key=True, nullable=False
    )
    logrun_id: Optional[int] = Field(
        default=None, foreign_key="logrun.id", primary_key=True, nullable=False
    )

class LogrunNpcencounterLink(SQLModel, table=True):
    npcencounter_id: Optional[int] = Field(
        default=None, foreign_key="npcencounter.id", primary_key=True, nullable=False
    )
    logrun_id: Optional[int] = Field(
        default=None, foreign_key="logrun.id", primary_key=True, nullable=False
    )

class Logrun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    trx_id: str
    action_seq: int
    block_time: str
    block_timestamp: int
    hour_handle: Optional[str]
    hour_handlestamp: Optional[int]
    day_handle: Optional[str]
    day_handlestamp: Optional[int]

    railroader: str
    railroader_reward: int
    run_complete: int
    run_start: int

    station_owner: str
    station_owner_reward: int
    arrive_station: str
    depart_station: str
    
    locomotives: List["Asset"] = Relationship(
        link_model=LogrunLocomotiveLink,
        sa_relationship_kwargs=dict(
            lazy="joined"
         ),
    )
    conductors: List["Asset"] = Relationship(
        link_model=LogrunConductorLink,
        sa_relationship_kwargs=dict(
            lazy="joined"
         ),
    )
    cars: List["Car"] = Relationship(
        link_model=LogrunCarLink,
        sa_relationship_kwargs=dict(
            lazy="joined"
         ),
    )
    logtips: List["Logtip"] = Relationship(link_model=LogrunTipsLink)
    npcs: List["Npcencounter"] = Relationship(link_model=LogrunNpcencounterLink)
    train_name: str
    weight: int
    century: str
    distance: int
    last_run_time: str
    last_run_tx: str

    fuel_type: str
    quantity: float
    
class Car(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    index: int
    type: str
    loads: List["Asset"] = Relationship(
        link_model=CarLoadLink,
        sa_relationship_kwargs=dict(
            lazy="joined"
         ),
    )
    car: List["Asset"] = Relationship(
        link_model=CarRailcarLink,
        sa_relationship_kwargs=dict(
            lazy="joined"
         ),
    )
class Usefuel(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)

    trx_id: str
    action_seq: int
    block_time:str
    block_timestamp: int

    fuel_type: str
    quantity: float
    railroader: str


class Buyfuel(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)

    trx_id: str
    action_seq: int
    block_time:str
    block_timestamp: int

    fuel_type: str
    quantity: float
    railroader: str
    century: str
    tocium_payed: float

class Npcencounter(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)

    trx_id: str
    action_seq: int
    block_time:str
    block_timestamp: int

    century: str
    npc: str
    railroader: str
    reward: int
    reward_symbol: str
    train: str
    

class Logtip(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)

    trx_id: str = Field(sa_column=Column("trx_id", String, unique=True))
    action_seq: int
    block_time:str
    block_timestamp: int

    total_tips: int
    before_tips: int
    railroader: str
    century: str
    train: str
    
    tips: List["Tip"] = Relationship(back_populates="logtip", sa_relationship_kwargs=dict(lazy="joined"))


class Tip(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)

    template_id: int
    criterion: str
    amount: int

    logtip_id: Optional[int] = Field(default=None, foreign_key="logtip.id")
    logtip: Optional[Logtip] = Relationship(back_populates="tips", sa_relationship_kwargs=dict(lazy="joined"))


class Template(SQLModel, table=True):

    template_id: int = Field(sa_column=Column("template_id", Integer, unique=True, primary_key=True, nullable=False))
    schema_name: str
    name: str
    cardid:int
    rarity:str
    img:str

    assets: List["Asset"] = Relationship(back_populates="template", sa_relationship_kwargs=dict(lazy="joined"))

    ## Passengercar
    weight: Optional[int]
    seats: Optional[int]

    ## Passenger
    tip: Optional[int]
    desc: Optional[str]
    criterion: Optional[str]
    threshold: Optional[int]
    home_region: Optional[str]
    home_regionid: Optional[int]
    
    ## Locomotive Specific
    fuel: Optional[str]
    speed: Optional[int]
    distance: Optional[int]
    composition: Optional[str]
    hauling_power: Optional[int]
    conductor_threshold: Optional[int]

    ## Conductor
    perk: Optional[str]
    perk_boost: Optional[int]
    perk2: Optional[str]
    perk_boost2: Optional[int]
    conductor_level: Optional[int]

    ## Railcar
    size: Optional[str]
    type: Optional[str]
    capacity: Optional[int]
    commodity_type: Optional[str]
    commodity_type2: Optional[str]

    ## Commodity
    
    volume: Optional[int]

    ## Station
    
    region: Optional[str]
    station_name: Optional[str]
    region_id: Optional[int]


class Asset(SQLModel, table=True):
    
    asset_id: str =  Field(sa_column=Column("asset_id", String, unique=True, primary_key=True, nullable=False))
    template_id: Optional[int] = Field(default=None, foreign_key="template.template_id")
    template: Optional[Template] = Relationship(back_populates="assets", sa_relationship_kwargs=dict(lazy="joined"))

    
    region: Optional[str]
    station_name: Optional[str]
    region_id: Optional[int]
    img: Optional[str]
