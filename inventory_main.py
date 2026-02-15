from fastapi import FastAPI
from pydantic import BaseModel
from typing import List,Optional
from fastapi import HTTPException
from fastapi import Header
from fastapi import Depends
from sqlmodel import SQLModel,Field,Session,create_engine,select
from contextlib import asynccontextmanager
app=FastAPI()
APIKEY="mysecret123"

engine=create_engine("sqlite:///inventory.db",echo=False)
def get_session():
    with Session(engine) as session:
        yield session
        
@asynccontextmanager
async def lifespan(app:FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
    
app=FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"status": "API is running"}

class productDB(SQLModel,table=True):
    id:Optional[int]=Field(default=None,primary_key=True)
    sku:str
    name:str
    price:float
    quantity:int
    
class productcreate(SQLModel):
    sku:str
    name:str
    price:float
    quantity:int

class productupdate(SQLModel):
    sku:Optional[str]
    name:Optional[str]
    price:Optional[float]
    quantity:Optional[int]
    
    
class SellRequest(SQLModel):
    amount:int
    
    
def require_api_key(x_api_key:str|None =Header(None)):
    if x_api_key != APIKEY:
        raise HTTPException(status_code=401,detail="invaild api key")
    
@app.post("/products",response_model=productDB)
def create_product(data:productcreate,session:Session=Depends(get_session),_=Depends(require_api_key)):
    existing=session.exec(select(productDB).where(productDB.sku==data.sku)).first()
    if existing:
        raise HTTPException(status_code=409,detail="suk already exist")
    if data.price <=0 or data.quantity <0:
        raise HTTPException(status_code=400,detail="price must be >0 and quantity must be >=0")  
    row=productDB(**data.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row

@app.get("/products",response_model=list[productDB])
def list_products(session:Session=Depends(get_session),_=Depends(require_api_key)):
    return session.exec(select(productDB)).all()

@app.get("/products/{id}",response_model=productDB)
def get_product(id:int,session:Session=Depends(get_session),_=Depends(require_api_key)):
    row=session.get(productDB,id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return row

@app.patch("/products/{id}",response_model=productDB)
def update_products(id:int,data:productupdate,session:Session=Depends(get_session),_=Depends(require_api_key)):
    row=session.get(productDB,id)
    if not row:
        raise HTTPException(status_code=404,detail="not found")
    updates=data.model_dump(exclude_unset=True)
    for k,v in updates.items():
        setattr(row,k,v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
@app.delete("/products/{id}")
def delete_product(id:int,session:Session=Depends(get_session),_=Depends(require_api_key)):
    row=session.get(productDB,id)
    if not row:
        raise HTTPException(status_code=404,detail="not found")
    session.delete(row)
    session.commit()
    return{"deleted":True,"id":id}
@app.post("/products/{id}/sell")
def products_sell(id:int,data:SellRequest, session:Session=Depends(get_session),_=Depends(require_api_key)):
    row=session.get(productDB,id)
    if not row:
        raise HTTPException(status_code=404,detail="not found")
    if data.amount <=0:
        raise HTTPException(status_code=400,detail="amount must be >0")
    if row.quantity < data.amount:
        raise HTTPException(status_code=409 ,detail="not enough stock")
    row.quantity=row.quantity-data.amount
    session.commit()
    session.refresh(row)
    return row
    
    



    
    




    
    