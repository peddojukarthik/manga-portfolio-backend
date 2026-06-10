from fastapi import FastAPI, APIRouter, HTTPException, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

ADMIN_KEY = os.environ.get('ADMIN_KEY', 'ninja-scroll-2026')

app = FastAPI(title="Manga Portfolio API")
api_router = APIRouter(prefix="/api")


# ---------- Models ----------
class VisitorCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    name: str = Field(min_length=1, max_length=100)
    contact: str = Field(min_length=1, max_length=200)


class Visitor(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reason: str
    name: str
    contact: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=1, max_length=4000)


class ContactMessage(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "Welcome to the Manga Portfolio scroll."}


@api_router.post("/visitors", response_model=Visitor)
async def create_visitor(payload: VisitorCreate):
    obj = Visitor(
        reason=payload.reason.strip(),
        name=payload.name.strip(),
        contact=payload.contact.strip() if payload.contact else None,
    )
    await db.visitors.insert_one(obj.model_dump())
    return obj


@api_router.get("/visitors", response_model=List[Visitor])
async def list_visitors(x_admin_key: Optional[str] = Header(default=None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized scroll-reader")
    docs = await db.visitors.find({}, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    return docs


@api_router.post("/contact", response_model=ContactMessage)
async def create_contact(payload: ContactCreate):
    obj = ContactMessage(name=payload.name.strip(), email=str(payload.email), message=payload.message.strip())
    await db.contact_messages.insert_one(obj.model_dump())
    return obj


@api_router.get("/contact", response_model=List[ContactMessage])
async def list_contacts(x_admin_key: Optional[str] = Header(default=None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized scroll-reader")
    docs = await db.contact_messages.find({}, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    return docs


@api_router.post("/admin/verify")
async def admin_verify(x_admin_key: Optional[str] = Header(default=None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Wrong scroll.")
    return {"ok": True}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
