from worker import writer, scanTemplates
from utils.manager import TrainManager
import time
from db import engine
from sqlmodel import Session
from models import Logrun,Usefuel, Template
import cachetool
import inspect
from disclog import postLog,postGeneric

def filler(posrr,posm) -> str:
    start=time.time()
    
    manager = TrainManager(posrr=posrr,
                           posm=posm)
    run = True

    postGeneric([("info","API init success! Logger started.")],"Startup")
  
    while run:
        try:
            manager.fetch()
            if len(manager.out) > 0:

                writer.delay(manager.out,"action")
                manager.out = []

        except Exception as e:
            postLog(e,"error",f"{inspect.stack()[0][3]}:{inspect.stack()[0][2]}")
            time.sleep(30)

    return f"{(time.time()-start)} total time"


if __name__ == "__main__":
    startup = True

    while startup:
        try:
            with Session(engine) as session:
                
                toptemp = session.query(Template).order_by(Template.template_id.desc()).first()
                posrrr = session.query(Logrun).order_by(Logrun.action_seq.desc()).first()
                posmr = session.query(Usefuel).order_by(Usefuel.action_seq.desc()).first()
            
            if toptemp:
                print("skipping init")
            else:
                cachetool.set_cache(f"last_templates",1622316652000)
                cachetool.set_cache(f"last_assets",1622316652000)
                scanTemplates()
                time.sleep(1200)
                
            if posrrr: posrr = posrrr.action_seq
            else: posrr = 1642127
            if posmr: posm = posmr.action_seq
            else: posm = 981927   

            filler(posrr,posm)
        except Exception as e:
                
                postLog(e,"warn",f"{inspect.stack()[0][3]}:{inspect.stack()[0][2]}")
                time.sleep(30)