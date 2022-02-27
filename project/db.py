

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, Session, SQLModel, create_engine, select
import inspect, config
from disclog import postLog

engine = create_engine(
    'postgresql://postgres:postgres@db:5432/foo', convert_unicode=True,
    pool_recycle=3600, pool_size=10)
db_session = scoped_session(sessionmaker(
    autocommit=False, autoflush=False, bind=engine))


def init_db():
    trying=True
    while trying:
        if engine:
            try:
                SQLModel.metadata.create_all(engine)
                trying=False
            except Exception as e:
                print(e)


def get_session():
    with Session(engine) as session:
        yield session


def commit_or_rollback(new_obj):
    with Session(engine) as session:
        try:
            session.add(new_obj)
            session.commit()
            session.refresh(new_obj)
        except Exception as e:
            postLog(e,"warn",f"{inspect.stack()[0][3]}:{inspect.stack()[0][2]}")
            session.rollback()
            return None
        finally:
            session.close()
        return new_obj


def query_raw(
    model,
    railroader:str=None,
    train:str=None,
    century:str=None,
    trx_id:str=None,
    before:str=None,
    after:str=None,
    fuel_type:config.FuelType=None,
    before_timestamp:int=None,
    after_timestamp:int=None,
    offset: int = 0,
    limit:int=10000,
    order:config.OrderChoose=config.OrderChoose.desc):

    query = select(model)
    if trx_id:
        query = query.where(model.trx_id==trx_id)
    if century:
        query = query.where(model.century==century)
    if train:
        query = query.where(model.train==train)
    if railroader:
        query = query.where(model.railroader==railroader)
    if fuel_type:
        query = query.where(model.fuel_type==fuel_type.value)

    
    if before:
        query = query.where(model.block_time<=before)
    if after:
        query = query.where(model.block_time>=after)
    if before_timestamp:
        query = query.where(model.block_timestamp<=before_timestamp)
    if after_timestamp:
        query = query.where(model.block_timestamp>after_timestamp)
    
    if order.value == 'desc':
        query = query.order_by(model.block_time.desc())
    else:
        query = query.order_by(model.block_time)

    with Session(engine) as session:
        out = session.exec(query.offset(offset).limit(limit)).all()
    
    return out