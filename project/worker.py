from datetime import datetime
from sqlmodel import Session, or_
from celery import Celery
from models import Logrun,Usefuel, Npcencounter,Car, Logtip, Tip, Template, Asset, Buyfuel
from db import db_session, engine, commit_or_rollback
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
            return Npcencounter(
                trx_id= act["action_trace"]["trx_id"],
                action_seq= act["account_action_seq"],
                block_time= act["block_time"],
                block_timestamp= int(blocktime.timestamp()),
                century = act["action_trace"]["act"]["data"]["century"],
                npc = act["action_trace"]["act"]["data"]["npc"],
                railroader = act["action_trace"]["act"]["data"]["railroader"],
                reward = int(float(act["action_trace"]["act"]["data"]["reward"].split(" ")[0])*10000),
                reward_symbol = act["action_trace"]["act"]["data"]["reward"].split(" ")[1],
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
            

@celery.task(base=SqlAlchemyTask)
def writer(to_write,mode) -> str:
    start=time.perf_counter()
    method = getattr(Builder(), f"create_new_{mode}")
    for item in to_write:
        new_item = method(item)
        if new_item:
            commit_or_rollback(new_item)
            
    return f"{(time.perf_counter()-start)} for {len(to_write)} items. mode: {mode}"
    