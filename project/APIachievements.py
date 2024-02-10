import os
import time

import aioredis
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.session import Session
from sqlmodel import Session, select

import config
from db import engine
from models import Achievement, Railroader

app = FastAPI(
    title="Train Century Achievement API",
    description="made with <3 by green",
    version="0.0.3",
    openapi_tags=config.achv_tags_metadata,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():

    redis = aioredis.from_url(
        os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379"), encoding="utf8", decode_responses=True
    )
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    print("redis cache success")


@app.get("/status", tags=["status"])
@cache(expire=10)
async def get_info_and_api_status():
    start = time.perf_counter()
    return {"query_time": time.perf_counter() - start, "data": {"hi": "ho"}}


@app.get("/roader", tags=["achievements"])
@cache(expire=5)
async def fetch_roaders(
    railroader: str = None,
    limit: int = Query(default=1000, le=1000),
    offset: int = 0,
    order: config.OrderChoose = config.OrderChoose.desc,
):
    start = time.perf_counter()

    with Session(engine) as session:
        query = select(Railroader)
        if railroader:
            query = query.where(Railroader.name == railroader)

        if order.value == "desc":
            query = query.order_by(Railroader.total_runs.desc())
        else:
            query = query.order_by(Railroader.total_runs)

        roaders = session.exec(query.offset(offset).limit(limit).options(selectinload(Railroader.achievements))).all()

        out = [
            {
                "roader_meta": roader,
                "achievements": [
            {
                "id":achiev.id,
                "achv_id": config.achv_mapped[f"{achiev.name} {achiev.tier}"],
                "railroader":achiev.railroader.name,
                "type":achiev.type,
                "criteria": achiev.criteria,
                "tier":  achiev.tier,
                "value": achiev.value,
                "name":achiev.name,
                "reached_date_timestamp": achiev.reached_date_timestamp,
                }
            for achiev in roader.achievements
        ]
            }
            for roader in roaders
        ]

    return {"query_time": time.perf_counter() - start, "data": out}


@app.get("/avs", tags=["achievements"])
@cache(expire=10)
async def fetch_avs(
    railroader: str = None,
    achv_id: int = None,
    type: str = None,
    criteria: str = None,
    name: str = None,
    tier: int = None,
    after: int = None,
    before: int = None,
    limit: int = Query(default=1000, le=1000),
    offset: int = 0,
    order: config.OrderChoose = config.OrderChoose.desc,
):
    start = time.perf_counter()
    with Session(engine) as session:
        query = select(Achievement)

        if railroader:
            query = query.where(Achievement.railroader.name == railroader)
        if type:
            query = query.where(Achievement.type == type)
        if criteria:
            query = query.where(Achievement.criteria == criteria)
        if name:
            query = query.where(Achievement.name == name)
        if tier:
            query = query.where(Achievement.tier == tier)
        if after:
            query = query.where(Achievement.reached_date_timestamp > after)
        if before:
            query = query.where(Achievement.reached_date_timestamp < before)

        if achv_id:
            named = list(config.achv_mapped.keys())[list(config.achv_mapped.values()).index(achv_id)].split(" ")
            query = query.where(Achievement.name == " ".join(named[:-1])).where(Achievement.tier == int(named[-1]))

        if order.value == "desc":
            query = query.order_by(Achievement.reached_date_timestamp.desc())
        else:
            query = query.order_by(Achievement.reached_date_timestamp)

        achievs = session.exec(query.offset(offset).limit(limit)).all()
        
        out = [
            {
                "id":achiev.id,
                "achv_id": config.achv_mapped[f"{achiev.name} {achiev.tier}"],
                "railroader":achiev.railroader.name,
                "type":achiev.type,
                "criteria": achiev.criteria,
                "tier":  achiev.tier,
                "value": achiev.value,
                "name":achiev.name,
                "reached_date_timestamp": achiev.reached_date_timestamp,
                }
            for achiev in achievs
        ]

    return {"query_time": time.perf_counter() - start, "data": out}


def format_achievements(achievs):
    return [
        {
            "id": achiev.id,
            "achv_id": config.achv_mapped[f"{achiev.name} {achiev.tier}"],
            "railroader": achiev.railroader.name,
            "type": achiev.type,
            "criteria": achiev.criteria,
            "tier": achiev.tier,
            "value": achiev.value,
            "name": achiev.name,
            "reached_date_timestamp": achiev.reached_date_timestamp,
        }
        for achiev in achievs
    ]
