import inspect
import time

from sqlmodel import Session

import cachetool
from db import engine, init_db
from disclog import postGeneric, postLog
from models import Logrun, Template, Usefuel
from utils.manager import TrainManager
from worker import scanTemplates, writer


def filler(posrr, posm) -> str:
    start = time.time()

    manager = TrainManager(posrr=posrr, posm=posm)
    run = True

    postGeneric([("info", "Success, filler started!")], "Startup")

    while run:
        try:
            manager.fetch()
            if len(manager.out) > 0:

                writer.delay(manager.out, "action")
                manager.out = []

        except Exception as e:
            postLog(e, "error", f"{inspect.stack()[0][3]}:{inspect.stack()[0][2]}")
            time.sleep(30)
        
        time.sleep(2)

    return f"{(time.time()-start)} total time"


if __name__ == "__main__":
    startup = True
    time.sleep(120)

    while startup:
        try:
            with Session(engine) as session:

                toptemp = session.query(Template).order_by(Template.template_id.desc()).first()
                posrrr = session.query(Logrun).order_by(Logrun.action_seq.desc()).first()
                posmr = session.query(Usefuel).order_by(Usefuel.action_seq.desc()).first()

            if toptemp:
                print("skipping init")
            else:

                cachetool.set_cache(f"last_templates", 1622316652000)
                cachetool.set_cache(f"last_assets", 1622316652000)
                scanTemplates()
            
            print(f"starting from {cachetool.get_cache('last_templates')} as last template, {cachetool.get_cache(f'last_assets')} for last asset")


            if posrrr:
                posrr = posrrr.action_seq
            else:
                posrr = 4453900
            if posmr:
                posm = posmr.action_seq
            else:
                posm = 2103900

            filler(posrr, posm)
        except Exception as e:

            postLog(e, "warn", f"{inspect.stack()[0][3]}:{inspect.stack()[0][2]}")
            time.sleep(30)
