from datetime import datetime
from sqlmodel import Session, or_
from celery import Celery
from models import Logrun,Usefuel, Npcencounter,Car, Logtip, Tip, Template, Asset, Buyfuel, Railroader, Achievement
from db import db_session, engine, commit_or_rollback
from sqlalchemy.orm import selectinload
import cachetool,config, os, time, inspect
from utils.nodes import AH, pick_best_waxnode
from disclog import postLog

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

class SqlAlchemyTask(celery.Task):
    abstract = True

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        db_session.remove()

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(60.0, Atomic.s(), name='routine to keep assets+templates updated')


@celery.task(base=SqlAlchemyTask)
def Atomic() -> str:
    start=time.perf_counter()
    try:
        scanTemplates()
    except Exception as e:
        postLog(e,"error",f"{inspect.stack()[0][3]}:{inspect.stack()[0][2]}")
            
    return f"atomic routine done,took: {(time.perf_counter()-start)} "

def fetchRoutine(mode,server):
    
    fetcher = getattr(AH(server=server), mode)
    after = cachetool.get_cache(f"last_{mode}")
    page = 1
    out = []
    running = True
    while running:
        try:
            jst = fetcher(page=page,after=after)
            for result in jst["data"]:
                if result["schema"]["schema_name"] in config.wanted_templates:
                    out.append(result)

            if len(jst["data"]) == 0:
                running=False
            else:
                try:
                    cachetool.set_cache(f"last_{mode}",int(jst["data"][-1]["minted_at_time"]))
                except Exception as e:
                    cachetool.set_cache(f"last_{mode}",int(jst["data"][-1]["created_at_time"]))

            if len(out) > 50000:
                running = False
            page += 1
            time.sleep(0.7)
        except Exception as e:
            postLog(e,"warn",f"{inspect.stack()[0][3]}:{inspect.stack()[0][2]}")
            time.sleep(10)
    return out

def scanTemplates():
    server= pick_best_waxnode("atomic",6)[0]
    templates = fetchRoutine("templates",server)
    assets = fetchRoutine("assets",server)
    
    writer.delay(templates,"template")
    if len(templates) > 100:
        time.sleep(5)
    writer.delay(assets,"asset")

    
class Builder():
    def create_new_action(self,act):

        blocktime = datetime.fromisoformat(act["block_time"])

        if act["action_trace"]["act"]["name"] == "logrun":

            with Session(engine) as session:
                full_cars = []
                for index,railcar in enumerate(act["action_trace"]["act"]["data"]["loads"]):
                    loads = session.query(Asset).filter(Asset.asset_id.in_(railcar["load_ids"])).all() if railcar["load_ids"] else None
                    car = session.query(Asset).filter(Asset.asset_id==railcar["railcar_asset_id"]).first() if railcar["railcar_asset_id"] else None
                    if car and loads:
                        stm = Car(
                            index=index,
                            car=[car],
                            loads=loads,
                            type=loads[0].template.schema_name if loads else "None"
                        )
                        session.add(stm)
                        full_cars.append(stm)
                    else:
                        print(act["action_trace"]["trx_id"],railcar)
                    
                try:
                    session.commit()
                except Exception as e:
                    print(e)
                    session.rollback()

                qry = session.query(Usefuel).filter(Usefuel.trx_id==act["action_trace"]["act"]["data"]["last_run_tx"]).first()
                tips = session.query(Logtip).filter(Logtip.trx_id==act["action_trace"]["trx_id"]).all()
                npcs = session.query(Npcencounter).filter(Npcencounter.trx_id==act["action_trace"]["trx_id"]).all()
                locos = session.query(Asset).filter(Asset.asset_id.in_(act["action_trace"]["act"]["data"]["locomotives"])).all()
                cons = session.query(Asset).filter(Asset.asset_id.in_(act["action_trace"]["act"]["data"]["conductors"])).all()


            if qry:
                fuel_type=qry.fuel_type
                quantity=qry.quantity
            else:
                print(f'trx not found: {act["action_trace"]["act"]["data"]["last_run_tx"]}')  
                fuel_type="COAL"
                quantity=0
            
            hrhandle = blocktime.strftime("20%y-%m-%dT%H:00:00.000")
            dayhandle = blocktime.strftime("20%y-%m-%dT00:00:00.000")

            return Logrun(
                trx_id= act["action_trace"]["trx_id"],
                action_seq= act["account_action_seq"],
                block_time= act["block_time"],
                block_timestamp= int(blocktime.timestamp()),
                hour_handle = hrhandle,
                hour_handlestamp = int(datetime.fromisoformat(hrhandle).timestamp()),
                day_handle = dayhandle,
                day_handlestamp = int(datetime.fromisoformat(dayhandle).timestamp()),
                railroader = act["action_trace"]["act"]["data"]["railroader"],
                railroader_reward = act["action_trace"]["act"]["data"]["railroader_reward"],
                run_complete = act["action_trace"]["act"]["data"]["run_complete"],
                run_start = act["action_trace"]["act"]["data"]["run_start"],
                locomotives =locos,
                conductors = cons,
                cars=full_cars,
                logtips=tips,
                npcs=npcs,
                station_owner = act["action_trace"]["act"]["data"]["station_owner"],
                station_owner_reward = act["action_trace"]["act"]["data"]["station_owner_reward"],
                train_name = act["action_trace"]["act"]["data"]["train_name"],
                weight = act["action_trace"]["act"]["data"]["weight"],
                arrive_station = act["action_trace"]["act"]["data"]["arrive_station"],
                century = act["action_trace"]["act"]["data"]["century"],
                depart_station = act["action_trace"]["act"]["data"]["depart_station"],
                distance = act["action_trace"]["act"]["data"]["distance"],
                last_run_time = act["action_trace"]["act"]["data"]["last_run_time"],
                last_run_tx = act["action_trace"]["act"]["data"]["last_run_tx"],
                fuel_type=fuel_type,
                quantity=quantity
            )

        if act["action_trace"]["act"]["name"] == "usefuel":
            return Usefuel(
                trx_id= act["action_trace"]["trx_id"],
                action_seq= act["account_action_seq"],
                block_time= act["block_time"],
                block_timestamp= int(blocktime.timestamp()),
                fuel_type = act["action_trace"]["act"]["data"]["quantity"].split(" ")[1],
                quantity = float(act["action_trace"]["act"]["data"]["quantity"].split(" ")[0]),
                railroader = act["action_trace"]["act"]["data"]["railroader"],
                
            )

        if act["action_trace"]["act"]["name"] == "buyfuel":
            return Buyfuel(
                trx_id= act["action_trace"]["trx_id"],
                action_seq= act["account_action_seq"],
                block_time= act["block_time"],
                block_timestamp= int(blocktime.timestamp()),
                fuel_type = act["action_trace"]["act"]["data"]["quantity"].split(" ")[1],
                quantity = float(act["action_trace"]["act"]["data"]["quantity"].split(" ")[0]),
                railroader = act["action_trace"]["act"]["data"]["railroader"],
                century = act["action_trace"]["act"]["data"]["century"],
                tocium_payed = float(act["action_trace"]["act"]["data"]["tocium"].split(" ")[0]),
                
            )

        if act["action_trace"]["act"]["name"] == "npcencounter":
            reward_symbol = act["action_trace"]["act"]["data"]["reward"].split(" ")[1]
            return Npcencounter(
                trx_id= act["action_trace"]["trx_id"],
                action_seq= act["account_action_seq"],
                block_time= act["block_time"],
                block_timestamp= int(blocktime.timestamp()),
                century = act["action_trace"]["act"]["data"]["century"],
                npc = act["action_trace"]["act"]["data"]["npc"],
                railroader = act["action_trace"]["act"]["data"]["railroader"],
                reward = float(act["action_trace"]["act"]["data"]["reward"].split(" ")[0]),
                reward_symbol = reward_symbol,
                train = act["action_trace"]["act"]["data"]["train"],
                
            )

        if act["action_trace"]["act"]["name"] == "logtips":
            return Logtip(
                    trx_id= act["action_trace"]["trx_id"],
                    action_seq= act["account_action_seq"],
                    block_time= act["block_time"],
                    block_timestamp= int(blocktime.timestamp()),
                    century = act["action_trace"]["act"]["data"]["century"],
                    railroader = act["action_trace"]["act"]["data"]["railroader"],
                    total_tips = int(act["action_trace"]["act"]["data"]["total_tips"]),
                    before_tips = int(act["action_trace"]["act"]["data"]["before_tips"]),
                    train = act["action_trace"]["act"]["data"]["train"],
                    tips= [ Tip(template_id = int(tipu["template_id"]), criterion = tipu["criterion"], amount = int(tipu["tip"])) for tipu in act["action_trace"]["act"]["data"]["tips"]],
                )

    def create_new_template(self,template):
        template_skeleton = Template(
                template_id=int(template["template_id"]),
                schema_name = template["schema"]["schema_name"],
                name=template["immutable_data"]["name"],
                cardid=template["immutable_data"]["cardid"],
                rarity=template["immutable_data"]["rarity"],
                img=template["immutable_data"]["img"] if ("img" in template["immutable_data"].keys()) else ""
        )

        if template["schema"]["schema_name"] == "passengercar":
            template_skeleton.weight = template["immutable_data"]["weight"]
            template_skeleton.seats = template["immutable_data"]["seats"]

        if template["schema"]["schema_name"] == "passenger":
            template_skeleton.tip = template["immutable_data"]["tip"]
            template_skeleton.desc = template["immutable_data"]["desc"]
            template_skeleton.criterion = template["immutable_data"]["criterion"]
            template_skeleton.threshold = template["immutable_data"]["threshold"]
            template_skeleton.home_region = template["immutable_data"]["home_region"]
            template_skeleton.home_regionid = template["immutable_data"]["home_regionid"]
        
        if template["schema"]["schema_name"] == "locomotive":
            template_skeleton.fuel = template["immutable_data"]["fuel"]
            template_skeleton.speed = template["immutable_data"]["speed"]
            template_skeleton.distance = template["immutable_data"]["distance"]
            template_skeleton.composition = template["immutable_data"]["composition"]
            template_skeleton.hauling_power = template["immutable_data"]["hauling_power"] if ("hauling_power" in template["immutable_data"].keys()) else None
            template_skeleton.conductor_threshold = template["immutable_data"]["conductor_threshold"] 

        if template["schema"]["schema_name"] == "conductor":
            template_skeleton.perk = template["immutable_data"]["perk"]
            template_skeleton.perk_boost = template["immutable_data"]["perk_boost"]
            template_skeleton.perk2 = template["immutable_data"]["perk2"] if ("perk2" in template["immutable_data"].keys()) else None
            template_skeleton.perk_boost2 = template["immutable_data"]["perk_boost2"] if ("perk_boost2" in template["immutable_data"].keys()) else None
            template_skeleton.conductor_level = template["immutable_data"]["conductor_level"]

        if template["schema"]["schema_name"] == "railcar":
            template_skeleton.size = template["immutable_data"]["size"]
            template_skeleton.type = template["immutable_data"]["type"]
            template_skeleton.capacity = template["immutable_data"]["capacity"]
            template_skeleton.commodity_type = template["immutable_data"]["commodity_type"]
            template_skeleton.commodity_type2 = template["immutable_data"]["commodity_type2"] if ("commodity_type2" in template["immutable_data"].keys()) else None

        if template["schema"]["schema_name"] == "commodity":
            template_skeleton.volume = template["immutable_data"]["volume"]
            template_skeleton.weight = template["immutable_data"]["weight"]
            template_skeleton.type = template["immutable_data"]["type"]
        
        if template["schema"]["schema_name"] == "station":
            template_skeleton.desc = template["immutable_data"]["desc"]

        return template_skeleton

    def create_new_asset(self,asset):
        
        asset_skeleton = Asset(
                asset_id=str(asset["asset_id"]),
                template_id = int(asset["template"]["template_id"]),
                )
        if asset["schema"]["schema_name"] == "station":
            asset_skeleton.img = asset["immutable_data"]["img"]
            asset_skeleton.region = asset["immutable_data"]["region"]
            asset_skeleton.region_id = asset["immutable_data"]["region_id"]

        return asset_skeleton

def compareTime(last,current):
    return (datetime.fromtimestamp(float(current)).date()-datetime.fromtimestamp(float(last)).date()).total_seconds()/3600


class AchievementProcessor():
    def process_logrun(self,act,typ):
        cuts = [5000,10000,20000, 35000, 50000]
        otto_cuts = [1,5,10, 18, 19]
        days = [7,30,90,180,365]
        days_dict = {
            "7":1,
            "30":2,
            "90":3,
            "180":4,
            "365":5
        }
        miles_dict = {
            "5000":1,
            "10000":2,
            "20000":3,
            "35000":4,
            "50000":5
        }
        otto_dict = {
            "1":1,
            "5":2,
            "10":3,
            "18":4,
            "19":5
        }
        miles_av_names = {
            "pallet": "Pallet Pusher",
            "crate": "Crate Carrier",
            "liquid": "Liquid Lifter",
            "gas": "Mr. Gas",
            "aggregate": "Woodchip King",
            "ore": "Rock Hustler",
            "granule": "Sugar Daddy",
            "grain": "Grainasaurus Rex",
            "perishable": "Icicle Jones",
            "oversized": "Big Shit Express",
            "building_materials": "Rob the Builder",
            "automobile": "OttoMobile",
            "top_secret": "Entity 9s BFF"
        }
        days_av_names = {
            "7":"7 Day Streak",
            "30":"30 Day Streak",
            "90":"90 Day Streak",
            "180":"180 Day Streak",
            "365":"365 Day Streak",
        }
        otto_av_names = {
            "1":"Otto’s Fellow",
            "5":"Otto’s Colleague",
            "10":"Otto’s Companion",
            "18":"Otto’s Enemy",
            "19":"Otto's Bro"
        }
        if typ == "logrun":

            with Session(engine) as session:
                existing = session.query(Railroader).filter(Railroader.name==act.railroader).first()
                distance = act.distance
                if existing:
                    existing.total_miles = existing.total_miles + distance
                    existing.total_runs = existing.total_runs + 1
                    
                    time_diff = compareTime(existing.last_run_stamp,act.block_timestamp)
                    if time_diff == 24.0:
                        existing.conseq_day += 1
                    if time_diff > 24.0:
                        
                        existing.conseq_day = 1
                    
                    existing.last_run_stamp = act.block_timestamp
                    coms_to_add = []
                    for car in act.cars:
                        for load in car.loads:
                        
                            if load.type:
                                if not load.type in coms_to_add:
                                    coms_to_add.append(load.type)
                    
                    for typ in coms_to_add:
                        field = f"total_miles_{typ}"
                        old_attr = getattr(existing, field)
                        setattr(existing,field,old_attr+distance)
                        for cut in cuts:
                            if old_attr+distance > cut:
                                found=False
                                for av in existing.achievements:
                                    
                                    if typ == av.type and av.value == cut:
                                        found=True
                                if found==False:
                                    new_av =Achievement(
                                        railroader_id= existing.id,
                                        railroader=existing,
                                        type= typ,
                                        criteria= "miles",
                                        tier= miles_dict[str(cut)],
                                        value= cut,
                                        name= miles_av_names[typ],
                                        reached= True,
                                        reached_date_timestamp= act.block_timestamp)
                                    session.add(new_av)
                                    
                    for day in days:
                        if existing.conseq_day > day:
                            found=False
                            for av in existing.achievements:
                                
                                if av.criteria == "days" and av.value == day:
                                    found=True
                            if found==False:
                                new_av =Achievement(
                                    railroader_id= existing.id,
                                    railroader=existing,
                                    type= "conseq_days",
                                    criteria= "days",
                                    tier= days_dict[str(day)],
                                    value= day,
                                    name= days_av_names[str(day)],
                                    reached= True,
                                    reached_date_timestamp= act.block_timestamp)
                                session.add(new_av)
                    session.add(existing)   
                                
                    try:
                        session.commit()
                    except Exception as e:
                        print(e)
                        session.rollback()
                    return None
                else:
                    return commit_or_rollback(Railroader(
                        name=act.railroader,
                        first_run_stamp = act.block_timestamp,
                        total_miles = distance,
                        total_runs = 1,
                        conseq_day = 1,
                        last_run_stamp = act.block_timestamp,
                        total_miles_pallet= 0,
                        total_miles_crate= 0,
                        total_miles_liquid= 0,
                        total_miles_gas= 0,
                        total_miles_aggregate= 0,
                        total_miles_ore= 0,
                        total_miles_granule= 0,
                        total_miles_grain= 0,
                        total_miles_perishable= 0,
                        total_miles_oversized= 0,
                        total_miles_building_materials= 0,
                        total_miles_automobile= 0,
                        total_miles_top_secret= 0,
                        achievements = [],
                        npc_encounter= 0,
                        otto_meets=0,
                        stranger_meets=0
                    ))

        if typ == "npcencounter":
            with Session(engine) as session:
                existing = session.query(Railroader).filter(Railroader.name==act.railroader).first()
                if existing:
                    existing.npc_encounter +=1
                    if act.npc.lower() == "otto": 
                        existing.otto_meets +=1
                        for otto in otto_cuts:
                            if existing.otto_meets == otto:
                                found=False
                                for av in existing.achievements:
                                    
                                    if av.criteria == "otto" and av.value == otto:
                                        found=True
                                if found==False:
                                    new_av =Achievement(
                                        railroader_id= existing.id,
                                        railroader=existing,
                                        type= "otto",
                                        criteria= "days",
                                        tier= otto_dict[str(otto)],
                                        value= otto,
                                        name= otto_av_names[str(otto)],
                                        reached= True,
                                        reached_date_timestamp= act.block_timestamp)
                                    session.add(new_av)
                                    
                    if act.npc.lower() == "stranger":
                        existing.stranger_meets +=1
                     
                        
                    session.add(existing)   
                                    
                    try:
                        session.commit()
                    except Exception as e:
                        print(e)
                        session.rollback()
                    return None
                else:
                    return commit_or_rollback(Railroader(
                        name=act.railroader,
                        first_run_stamp = act.block_timestamp,
                        total_miles = 0,
                        total_runs = 1,
                        conseq_day = 1,
                        last_run_stamp = act.block_timestamp,
                        total_miles_pallet= 0,
                        total_miles_crate= 0,
                        total_miles_liquid= 0,
                        total_miles_gas= 0,
                        total_miles_aggregate= 0,
                        total_miles_ore= 0,
                        total_miles_granule= 0,
                        total_miles_grain= 0,
                        total_miles_perishable= 0,
                        total_miles_oversized= 0,
                        total_miles_building_materials= 0,
                        total_miles_automobile= 0,
                        total_miles_top_secret= 0,
                        achievements = [],
                        npc_encounter= 1,
                        otto_meets=0,
                        stranger_meets=1
                    ))
                    

@celery.task(base=SqlAlchemyTask)
def writer(to_write,mode) -> str:
    start=time.perf_counter()
    processor = AchievementProcessor()
    method = getattr(Builder(), f"create_new_{mode}")
    for item in to_write:
        new_item = method(item)
        if new_item:
            commited_item = commit_or_rollback(new_item)
            if commited_item and mode == "action":
                if item["action_trace"]["act"]["name"] in ["logrun","npcencounter"]:
                    processor.process_logrun(commited_item,item["action_trace"]["act"]["name"])
                
            
    return f"{(time.perf_counter()-start)} for {len(to_write)} items. mode: {mode}"
    