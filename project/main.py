
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import selectinload, lazyload
from fastapi import FastAPI, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from models import Logrun,Usefuel,Npcencounter, Logtip, Tip, Asset,Template, Buyfuel
from sqlmodel import Session, select, or_
from sqlalchemy import func,desc, cast, String
from sqlalchemy.dialects.postgresql import array
from db import engine, get_session, query_raw
from collections import Counter
import config, aioredis, os,time
from datetime import datetime, timedelta
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

app = FastAPI(title="Train Century History API",
        description="made with <3 by green",
        version="0.1.7",
        openapi_tags=config.tags_metadata)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    
    redis =  aioredis.from_url(os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379"), encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    print("redis cache success")

@app.get("/status", tags=["status"])
@cache(expire=10)
async def get_info_and_api_status():
    start = time.perf_counter()
    query = select([func.count()])
    with Session(engine) as session:
        posrrr = session.query(Logrun).order_by(Logrun.action_seq.desc()).first()
        posmr = session.query(Usefuel).order_by(Usefuel.action_seq.desc()).first()
        countl = session.exec(query.select_from(Logrun)).all()
        countu = session.exec(query.select_from(Usefuel)).all()

    filler_info={
        "online": True,
        "last_logrun": posrrr.block_time if posrrr else "None",
        "last_usefuel": posmr.block_time if posmr else "None",
    }
    db_info={
        "logrun_count": countl[0],
        "logrun_last_action_seq": posrrr.action_seq if posrrr else "None",
        "usefuel_count": countu[0],
        "usefuel_last_action_seq": posmr.action_seq if posmr else "None"
        
    }
    return {"query_time":time.perf_counter()-start,"data":{"filler_state":filler_info,"db_state":db_info}}


@app.get("/station", tags=["stations"])
@cache(expire=5)
async def station_owner_dashboard_query_v3(
            station:str,
            timeframe:int=24,
            ):
    start = time.perf_counter()
    q2=None
    q3=None
    with Session(engine) as session:

        qry = session.query(
                        Logrun.arrive_station.label("station"),
                        func.array_agg(Logrun.station_owner).label("owner"),
                        func.count(Logrun.arrive_station).label("total_transports"), 
                        func.sum(Logrun.station_owner_reward).label("total_reward"),
                        (func.sum(Logrun.station_owner_reward)/func.count(Logrun.arrive_station)).label("avg_reward"),
                        func.array_agg(array([cast(Logrun.station_owner_reward, String),cast(Logrun.block_timestamp, String),Logrun.railroader])).label('comissions_list'),
                        func.array_agg(Logrun.railroader).label('unique_visitors'),
                        func.array_agg(Logrun.depart_station).label('refering_stations')
                        ).filter(Logrun.arrive_station==station)
        
        if timeframe != 0:
            qry = qry.filter(Logrun.block_time>=(datetime.utcnow()-timedelta(hours=timeframe)).isoformat()[:-3])

        if timeframe < 51 and timeframe > 0:
            qry2 = session.query(
                            Logrun.hour_handlestamp.label("hour"),
                            func.count(Logrun.arrive_station).label("hr_transports"), 
                            func.sum(Logrun.station_owner_reward).label("hr_reward"),
                            func.array_agg(Logrun.railroader).label('unique_visitors'),
                            ).filter(Logrun.arrive_station==station)
            
            qry2 = qry2.filter(Logrun.block_time>=(datetime.utcnow()-timedelta(hours=timeframe)).isoformat()[:-3])
            q2 = qry2.group_by(Logrun.hour_handlestamp).order_by(desc("hour")).limit(2000).distinct()

        if timeframe > 50 or timeframe == 0:

            qry3 = session.query(
                            Logrun.day_handlestamp.label("day"),
                            func.count(Logrun.arrive_station).label("day_transports"), 
                            func.sum(Logrun.station_owner_reward).label("day_reward"),
                            func.array_agg(Logrun.railroader).label('unique_visitors')
                            ).filter(Logrun.arrive_station==station)

            if timeframe != 0:
                qry3 = qry3.filter(Logrun.block_time>=(datetime.utcnow()-timedelta(hours=timeframe)).isoformat()[:-3])          
            q3 = qry3.group_by(Logrun.day_handlestamp).order_by(desc("day")).limit(1000).distinct()

        q = qry.group_by(Logrun.arrive_station).order_by(desc("total_transports")).first()

        if q:
            out= {
                "station" : q["station"],
                "owner" : q["owner"][-1],
                "total_transports" : q["total_transports"],
                "total_comission" : q["total_reward"]/10000,
                "avg_comission" : q["avg_reward"]/10000,
                "top_visitors" : Counter(q['unique_visitors']),
                "refering_stations" : Counter(q['refering_stations']),
                "days": [{
                    "day":hr["day"],
                    "tocium":hr["day_reward"],
                    "unique_visitors":len(set(hr["unique_visitors"])),
                    "total_visitors": hr["day_transports"],
                } for hr in q3] if q3 else [],
                "hours": [{
                    "hour":hr["hour"],
                    "tocium":hr["hr_reward"],
                    "unique_visitors":len(set(hr["unique_visitors"])),
                    "total_visitors": hr["hr_transports"],
                } for hr in q2] if q2 else [],
                "comissions_list" : [(int(c[0]),int(c[1]),c[2]) for c in q['comissions_list']],
            }
        else:
            return {"query_time":time.perf_counter()-start,"data":[]}
        
    return {"query_time":time.perf_counter()-start,"data":out}

@app.get("/stations", tags=["stations"])
@cache(expire=5)
async def get_station_aggregated_and_ordered(
            owner:str=None,
            timeframe:int=24,
            limit:int=Query(default=1000, lte=1000)):
    start = time.perf_counter()
    with Session(engine) as session:

        qry = session.query(
                        Logrun.arrive_station.label("station"),
                        func.array_agg(Logrun.station_owner).label("owner"),
                        func.count(Logrun.arrive_station).label("total_transports"), 
                        func.sum(Logrun.station_owner_reward).label("total_reward"),
                        (func.sum(Logrun.station_owner_reward)/func.count(Logrun.arrive_station)).label("avg_reward"),
                        func.sum(Logrun.weight).label("total_weight"), 
                        (func.sum(Logrun.weight)/func.count(Logrun.arrive_station)).label("avg_weight"),
                        func.array_agg(Logrun.railroader).label('roaders')
                        )
        if owner:
            qry = qry.filter(Logrun.station_owner==owner)
        if timeframe != 0:
            qry = qry.filter(Logrun.block_time>=(datetime.utcnow()-timedelta(hours=timeframe)).isoformat()[:-3])

        qry = qry.group_by(Logrun.arrive_station).order_by(desc("total_transports")).limit(limit).distinct()
        out=[
            {
                "station" : q["station"],
                "owner" : q["owner"][-1],
                "total_transports" : q["total_transports"],
                "total_comission" : q["total_reward"]/10000,
                "avg_comission" : q["avg_reward"]/10000,
                "total_weight" : q["total_weight"],
                "avg_weight" : q["avg_weight"],
                "visitors" : Counter(q["roaders"])
            }
            for q in qry
        ]

    return {"query_time":time.perf_counter()-start,"count":len(out),"data":out}

@app.get("/railroader", tags=["railroaders"])
@cache(expire=5)
async def get_railroader_dashboard(
            railroader:str=None,
            before:str=None,
            after:str=None,
            timeframe:int=24):
    start = time.perf_counter()

    with Session(engine) as session:
        qry = session.query(
                        Logrun.railroader.label("name"),
                        
                        func.count(Logrun.arrive_station).label("total_transports"), 
                        func.sum(Logrun.railroader_reward).label("total_reward"),
                        func.sum(Logrun.distance).label("total_distance"),
                        (func.sum(Logrun.railroader_reward)/func.count(Logrun.arrive_station)).label("avg_reward"),
                        func.sum(Logrun.weight).label("total_weight"), 
                        (func.sum(Logrun.weight)/func.count(Logrun.arrive_station)).label("avg_weight"),
                        func.array_agg(Logrun.arrive_station).label('stations'),
                        func.sum(Logrun.quantity).filter(Logrun.fuel_type=="DIESEL").label('total_diesel'),
                        func.sum(Logrun.quantity).filter(Logrun.fuel_type=="COAL").label('total_coal'),
                        )
        if railroader:
            qry = qry.filter(Logrun.railroader==railroader)
        if before:
            qry = qry.filter(Logrun.block_time<=before)
        if after:
            qry = qry.filter(Logrun.block_time>after)
        if timeframe != 0:
            qry = qry.filter(Logrun.block_time>=(datetime.utcnow()-timedelta(hours=timeframe)).isoformat()[:-3])


        qry = qry.group_by(Logrun.railroader).order_by(desc("total_transports")).distinct()

        out=[
            {
                "name" : q["name"],
                "total_transports" : q["total_transports"],
                "total_distance" : q["total_distance"],
                "total_reward" : q["total_reward"]/10000,
                "avg_reward" : q["avg_reward"]/10000,
                "total_weight" : q["total_weight"],
                "avg_weight" : q["avg_weight"],
                "total_coal" : round(q["total_coal"],2) if q["total_coal"] else 0,
                "avg_coal" : round(q["total_coal"]/q["total_transports"],2) if q["total_coal"] else 0,
                "total_diesel" : round(q["total_diesel"],2) if q["total_diesel"] else 0,
                "avg_diesel" :  round(q["total_diesel"]/q["total_transports"],2) if q["total_diesel"] else 0,
                "visited_stations" : Counter(q["stations"])
            }
            for q in qry
        ]

    return {"query_time":time.perf_counter()-start,"count":len(out),"data":out}

@app.get("/railroaders", tags=["railroaders"])
@cache(expire=5)
async def get_railroader_aggregated_and_ordered(
            before:str=None,
            after:str=None,
            limit:int=Query(default=1000, lte=1000)):
    start = time.perf_counter()

    with Session(engine) as session:
        qry = session.query(
                        Logrun.railroader.label("name"),
                        
                        func.count(Logrun.arrive_station).label("total_transports"), 
                        func.sum(Logrun.railroader_reward).label("total_reward"),
                        func.sum(Logrun.distance).label("total_distance"),
                        (func.sum(Logrun.railroader_reward)/func.count(Logrun.arrive_station)).label("avg_reward"),
                        func.sum(Logrun.weight).label("total_weight"), 
                        (func.sum(Logrun.weight)/func.count(Logrun.arrive_station)).label("avg_weight"),
                        func.array_agg(Logrun.arrive_station).label('stations'),
                        func.sum(Logrun.quantity).filter(Logrun.fuel_type=="DIESEL").label('total_diesel'),
                        func.sum(Logrun.quantity).filter(Logrun.fuel_type=="COAL").label('total_coal'),
                        )
        if before:
            qry = qry.filter(Logrun.block_time<=before)
        if after:
            qry = qry.filter(Logrun.block_time>after)
        else:
            qry = qry.filter(Logrun.block_time>=(datetime.utcnow()-timedelta(hours=24)).isoformat()[:-3])

        qry = qry.group_by(Logrun.railroader).order_by(desc("total_transports")).limit(limit).distinct()

        out=[
            {
                "name" : q["name"],
                "total_transports" : q["total_transports"],
                "total_distance" : q["total_distance"],
                "total_reward" : q["total_reward"]/10000,
                "avg_reward" : q["avg_reward"]/10000,
                "total_weight" : q["total_weight"],
                "avg_weight" : q["avg_weight"],
                "total_coal" : round(q["total_coal"],2) if q["total_coal"] else 0,
                "avg_coal" : round(q["total_coal"]/q["total_transports"],2) if q["total_coal"] else 0,
                "total_diesel" : round(q["total_diesel"],2) if q["total_diesel"] else 0,
                "avg_diesel" :  round(q["total_diesel"]/q["total_transports"],2) if q["total_diesel"] else 0,
                "visited_stations" : Counter(q["stations"])
            }
            for q in qry
        ]

    return {"query_time":time.perf_counter()-start,"count":len(out),"data":out}


@app.get("/admin_dash", tags=["admin"])
@cache(expire=10)
async def get_railroader_dashboard(
            century:str=None,
            before:str=None,
            after:str=None,
            timeframe:int=24):
    start = time.perf_counter()

    with Session(engine) as session:
        qry = session.query(
                        
                        func.count(Logrun.arrive_station).label("total_transports"), 
                        func.sum(Logrun.railroader_reward).label("total_reward"),
                        func.sum(Logrun.distance).label("total_distance"),
                        (func.sum(Logrun.railroader_reward)/func.count(Logrun.arrive_station)).label("avg_reward"),
                        func.sum(Logrun.weight).label("total_weight"), 
                        (func.sum(Logrun.weight)/func.count(Logrun.arrive_station)).label("avg_weight"),
                        func.sum(Logrun.quantity).filter(Logrun.fuel_type=="DIESEL").label('total_diesel'),
                        func.sum(Logrun.quantity).filter(Logrun.fuel_type=="COAL").label('total_coal'),
                        func.array_agg(Logrun.railroader).label('unique_roaders'),
                        func.array_agg(Logrun.train_name).label('unique_trains')
                        )
        if before:
            qry = qry.filter(Logrun.block_time<=before)
        if after:
            qry = qry.filter(Logrun.block_time>after)
        
        if century:
            qry = qry.where(Logrun.century==century)
        if timeframe != 0:
            qry = qry.filter(Logrun.block_time>=(datetime.utcnow()-timedelta(hours=timeframe)).isoformat()[:-3])


        q = qry.first()

        out={
                "total_transports" : q["total_transports"],
                "total_distance" : q["total_distance"],
                "total_reward" : q["total_reward"]/10000,
                "avg_reward" : q["avg_reward"]/10000,
                "total_weight" : q["total_weight"],
                "avg_weight" : q["avg_weight"],
                "total_coal" : round(q["total_coal"],2) if q["total_coal"] else 0,
                "avg_coal" : round(q["total_coal"]/q["total_transports"],2) if q["total_coal"] else 0,
                "total_diesel" : round(q["total_diesel"],2) if q["total_diesel"] else 0,
                "avg_diesel" :  round(q["total_diesel"]/q["total_transports"],2) if q["total_diesel"] else 0,
                "active_railroaders":len(set(q["unique_roaders"])),
                "active_trains":len(set(q["unique_trains"])),
            }
    
    return {"query_time":time.perf_counter()-start,"data":out}

@app.get("/buyfuel_aggregate", tags=["admin"])
@cache(expire=5)
async def get_aggregated_buyfuels(
            timeframe:int=24,
            simple:bool=True):
    start = time.perf_counter()

    with Session(engine) as session:

        qry = session.query(
                        Buyfuel.fuel_type.label("type"),
                        func.count(Buyfuel.railroader).label("total_buys"), 
                        func.sum(Buyfuel.quantity).label("total_quantity"),
                        func.sum(Buyfuel.tocium_payed).label("total_tocium_spent"),
                        )
        if not simple:
            qry2 = session.query(
                            Buyfuel.railroader.label("railroader"),
                            func.count(Buyfuel.railroader).filter(Buyfuel.fuel_type=="COAL").label("total_buys_coal"), 
                            func.sum(Buyfuel.quantity).filter(Buyfuel.fuel_type=="COAL").label('total_coal'),
                            func.sum(Buyfuel.tocium_payed).filter(Buyfuel.fuel_type=="COAL").label('total_tocium_for_coal'),
                            func.count(Buyfuel.railroader).filter(Buyfuel.fuel_type=="DIESEL").label("total_buys_diesel"), 
                            func.sum(Buyfuel.quantity).filter(Buyfuel.fuel_type=="DIESEL").label('total_diesel'),
                            func.sum(Buyfuel.tocium_payed).filter(Buyfuel.fuel_type=="DIESEL").label('total_tocium_for_diesel'),
                            )
            qry2 = qry2.filter(Buyfuel.block_time>=(datetime.utcnow()-timedelta(hours=timeframe)).isoformat()[:-3]).group_by(Buyfuel.railroader).all()

        if timeframe != 0:
            qry = qry.filter(Buyfuel.block_time>=(datetime.utcnow()-timedelta(hours=timeframe)).isoformat()[:-3])


        qry = qry.group_by(Buyfuel.fuel_type).all()

        out = {
            "totals":qry,
            "railroaders":qry2 if simple else None
        }
        
    
    return {"query_time":time.perf_counter()-start,"data":out}

def buildCar(car):
    build = {
        "index": car.index,
    }
    
    if car.type == "commodity":
        railcar = car.car[0]
        build["car"]= {
            "name":railcar.template.name,
            "cardid":railcar.template.cardid,
            "size":railcar.template.size,
            "capacity":railcar.template.capacity,
            "rarity":railcar.template.rarity,
            "type":railcar.template.type,
            "commodity_type":railcar.template.commodity_type,
            "commodity_type2":railcar.template.commodity_type2
        }
        build["loads"]= [{
                    "name":load.template.name,
                    "cardid":load.template.cardid,
                    "volume":load.template.volume,
                    "weight":load.template.weight,
                    "rarity":load.template.rarity,
                    "type":load.template.type} for load in car.loads]
                    
    if car.type == "passenger":
        passengercar = car.car[0]
        build["car"]= {
                    "name":passengercar.template.name,
                    "cardid":passengercar.template.cardid,
                    "seats":passengercar.template.seats,
                    "weight":passengercar.template.weight,
                    "rarity":passengercar.template.rarity
        }
        build["loads"]= [{
                    "name":passenger.template.name,
                    "cardid":passenger.template.cardid,
                    "tip":passenger.template.tip,
                    "criterion":passenger.template.criterion,
                    "rarity":passenger.template.rarity,
                    "treshold":passenger.template.threshold,
                    "home_region":passenger.template.home_region,
                    "home_regionid":passenger.template.home_regionid,} for passenger in car.loads]
    return build
                
@app.get("/logrun" , tags=["admin"], response_model_exclude_defaults=True)
@cache(expire=5)
async def get_raw_logrun_actions(
              railroader:str=None,
              arrive_station:str=None,
              depart_station:str=None,
              station_owner:str=None,
              century:str=None,
              train_name:str=None,
              before:str=None,
              after:str=None,
              before_timestamp:int=None,
              after_timestamp:int=None,
              offset: int = 0,
              limit:int=Query(default=1000, lte=1000),
              simple:bool=True,
              order:config.OrderChoose=config.OrderChoose.desc,
              session: Session = Depends(get_session),
              ):
    start = time.perf_counter()
    query = select(Logrun)
    if depart_station:
        query = query.where(Logrun.depart_station==depart_station)
    if arrive_station:
        query = query.where(Logrun.arrive_station==arrive_station)
    if railroader:
        query = query.where(Logrun.railroader==railroader)
    if station_owner:
        query = query.where(Logrun.station_owner==station_owner)
    if train_name:
        query = query.where(Logrun.train_name==train_name)
    if century:
        query = query.where(Logrun.century==century)
    if before:
        query = query.where(Logrun.block_time<=before)
    if after:
        query = query.where(Logrun.block_time>after)
    
    if before_timestamp:
        query = query.where(Logrun.block_timestamp<=before_timestamp)
    if after_timestamp:
        query = query.where(Logrun.block_timestamp>after_timestamp)
    
    if order.value == 'desc':
        query = query.order_by(Logrun.block_time.desc())
    else:
        query = query.order_by(Logrun.block_time)
    
    if simple:
            transports = session.exec(query.options(lazyload('cars')).options(lazyload('locomotives')).options(lazyload('conductors')).offset(offset).limit(limit)).all()
    
            out = [
                    {
                "trx_id": trans.trx_id,
                # "action_seq": trans.action_seq,
                "block_time": trans.block_time,
                "block_timestamp": trans.block_timestamp,
                "railroader": trans.railroader,
                "railroader_reward": trans.railroader_reward,
                "run_complete": trans.run_complete,
                "run_start": trans.run_start,
                "station_owner": trans.station_owner,
                "station_owner_reward": trans.station_owner_reward,
                "arrive_station": trans.arrive_station,
                "depart_station": trans.depart_station,
                "train_name": trans.train_name,
                "weight": trans.weight,
                "century": trans.century,
                "distance": trans.distance,
                "last_run_time": trans.last_run_time,
                "last_run_tx": trans.last_run_tx,
                "fuel_type": trans.fuel_type,
                "quantity": trans.quantity
            }
            for trans in transports
        ]
    
    else:
        transports = session.exec(query.offset(offset).limit(limit).options(selectinload(Logrun.cars)).options(selectinload(Logrun.logtips)).options(selectinload(Logrun.npcs)).options(selectinload(Logrun.locomotives)).options(selectinload(Logrun.conductors))).all()
    
        out = [
                    {
                "trx_id": trans.trx_id,
                # "action_seq": trans.action_seq,
                "block_time": trans.block_time,
                "block_timestamp": trans.block_timestamp,
                "railroader": trans.railroader,
                "cars": [buildCar(car) for car in trans.cars],
                "locomotives": [{
                    "name":loc.template.name,
                    "cardid":loc.template.cardid,
                    "speed":loc.template.speed,
                    "distance":loc.template.distance,
                    "composition":loc.template.composition,
                    "rarity":loc.template.rarity,
                    "hauling_power":loc.template.hauling_power,
                    "conductor_threshold":loc.template.conductor_threshold} for loc in trans.locomotives],
                "conductors": [{
                    "name":con.template.name,
                    "cardid":con.template.cardid,
                    "conductor_level":con.template.conductor_level,
                    "perk":con.template.perk,
                    "perk_boost":con.template.perk_boost,
                    "perk2":con.template.perk2,
                    "perk_boost2":con.template.perk_boost2} for con in trans.conductors],
                "logtip": {
                    "total_tips":trans.logtips[0].total_tips,
                    "before_tips": trans.logtips[0].before_tips,
                    "tips":trans.logtips[0].tips} if len(trans.logtips) > 0  else {},
                "npcencounter":trans.npcs,
                "railroader_reward": trans.railroader_reward,
                "run_complete": trans.run_complete,
                "run_start": trans.run_start,
                "station_owner": trans.station_owner,
                "station_owner_reward": trans.station_owner_reward,
                "arrive_station": trans.arrive_station,
                "depart_station": trans.depart_station,
                "train_name": trans.train_name,
                "weight": trans.weight,
                "century": trans.century,
                "distance": trans.distance,
                "last_run_time": trans.last_run_time,
                "last_run_tx": trans.last_run_tx,
                "fuel_type": trans.fuel_type,
                "quantity": trans.quantity
            }
            for trans in transports
        ]

    
    return {"query_time":time.perf_counter()-start,"data":out}

@app.get("/usefuel" , tags=["admin"])
@cache(expire=5)
async def get_raw_usefuel_actions(
                railroader:str=None,
                trx_id:str=None,
                before:str=None,
                after:str=None,
                fuel_type:config.FuelType=None,
                before_timestamp:int=None,
                after_timestamp:int=None,
                offset: int = 0,
                limit:int=Query(default=1000, lte=10000),
                order:config.OrderChoose=config.OrderChoose.desc):
    start = time.perf_counter()

    fueluses = query_raw(
        Usefuel,
        railroader=railroader,
        trx_id=trx_id,
        before=before,
        after=after,
        fuel_type=fuel_type,
        before_timestamp=before_timestamp,
        after_timestamp=after_timestamp,
        offset=offset,
        limit=limit,
        order=order
    )
    
    return {"query_time":time.perf_counter()-start,"data":fueluses}

@app.get("/buyfuel" , tags=["admin"])
@cache(expire=5)
async def get_raw_buyfuel_actions(
                railroader:str=None,
                trx_id:str=None,
                before:str=None,
                after:str=None,
                fuel_type:config.FuelType=None,
                before_timestamp:int=None,
                after_timestamp:int=None,
                offset: int = 0,
                limit:int=Query(default=1000, lte=10000),
                order:config.OrderChoose=config.OrderChoose.desc):
    start = time.perf_counter()

    buyfuel = query_raw(
        Buyfuel,
        railroader=railroader,
        trx_id=trx_id,
        before=before,
        after=after,
        fuel_type=fuel_type,
        before_timestamp=before_timestamp,
        after_timestamp=after_timestamp,
        offset=offset,
        limit=limit,
        order=order
    )
    
    return {"query_time":time.perf_counter()-start,"data":buyfuel}


@app.get("/npcencounter" , tags=["admin"])
@cache(expire=5)
async def get_raw_npcecnounter_actions(
                railroader:str=None,
                train:str=None,
                century:str=None,
                trx_id:str=None,
                before:str=None,
                after:str=None,
                before_timestamp:int=None,
                after_timestamp:int=None,
                offset: int = 0,
                limit:int=Query(default=1000, lte=10000),
                order:config.OrderChoose=config.OrderChoose.desc):
    start = time.perf_counter()
    
    npcs = query_raw(
        Npcencounter,
        railroader=railroader,
        trx_id=trx_id,
        before=before,
        after=after,
        train=train,
        century=century,
        before_timestamp=before_timestamp,
        after_timestamp=after_timestamp,
        offset=offset,
        limit=limit,
        order=order
    )
    return {"query_time":time.perf_counter()-start,"data":npcs}

@app.get("/logtips" , tags=["admin"])
@cache(expire=5)
async def get_raw_logtips_actions(
                session: Session = Depends(get_session),
                railroader:str=None,
                train:str=None,
                century:str=None,
                trx_id:str=None,
                before:str=None,
                after:str=None,
                before_timestamp:int=None,
                after_timestamp:int=None,
                offset: int = 0,
                limit:int=Query(default=1000, lte=10000),
                order:config.OrderChoose=config.OrderChoose.desc):
    start = time.perf_counter()
    query = select(Logtip)
    if trx_id:
        query = query.where(Logtip.trx_id==trx_id)
    if century:
        query = query.where(Logtip.century==century)
    if train:
        query = query.where(Logtip.train==train)
    if railroader:
        query = query.where(Logtip.railroader==railroader)
    if before:
        query = query.where(Logtip.block_time<=before)
    if after:
        query = query.where(Logtip.block_time>after)
    
    if before_timestamp:
        query = query.where(Logtip.block_timestamp<=before_timestamp)
    if after_timestamp:
        query = query.where(Logtip.block_timestamp>after_timestamp)

    if order.value == 'desc':
        query = query.order_by(Logtip.block_time.desc())
    else:
        query = query.order_by(Logtip.block_time)
    
    tips = session.exec(query.offset(offset).limit(limit).options(selectinload(Logtip.tips))).all()
    
    out = [
        { 
            "railroader":tip.railroader,
            "total_tips":tip.total_tips,
            "before_tips": tip.before_tips,
            "century":  tip.century,
            "train": tip.train,
            "tips":tip.tips,
            "block_time": tip.block_time,
            "block_timestamp": tip.block_timestamp,
            }
        for tip in tips
    ]

    return {"query_time":time.perf_counter()-start,"data":out}

@app.get("/asset" , tags=["atomic"],response_model=Template, response_model_exclude_defaults=True)
@cache(expire=5)
async def get_template_for_asset_by_id(
                asset_id: int,
                session: Session = Depends(get_session),
                ):

    query = select(Asset)
    if asset_id:
        query = query.where(Asset.asset_id==str(asset_id))
    
    asset = session.exec(query.options(selectinload(Asset.template))).first()

    if asset.template.schema_name == "station":
        out = {
            "schema_name":asset.template.schema_name,
            "template_id":asset.template_id,
            "region": asset.region,
            "region_id": asset.region_id,
            "img": asset.img,
            "name": asset.template.name,
            "cardid": asset.template.cardid,
            "rarity": asset.template.rarity,
            "desc": asset.template.desc
        }
    else:
        out = asset.template
    return out

@app.get("/template" , tags=["atomic"],response_model=Template,response_model_exclude_defaults=True)
@cache(expire=5)
async def get_template_by_id(
                template_id: int,
                session: Session = Depends(get_session),
                ):
    with Session(engine) as session:
        template = session.get(Template, template_id)
        return template