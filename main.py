# agrimove/backend/main.py

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="AgriMove API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Configuration
SECRET_KEY = "your-secret-key-here"  # In production, use a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password handling
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database simulation (replace with real database in production)
users_db = {
    "farmer1": {
        "username": "farmer1",
        "full_name": "John Farmer",
        "email": "farmer1@example.com",
        "hashed_password": pwd_context.hash("password"),
        "disabled": False
    }
}

transport_requests = []

# Models
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class TransportRequest(BaseModel):
    farmer_name: str = Field(..., min_length=2)
    produce: str = Field(..., min_length=2)
    quantity: int = Field(..., gt=0)
    pickup: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)
    status: str = "Pending"
    created_at: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None

# Security Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(username: str, password: str):
    user = get_user(users_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# Error Handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/request", response_model=TransportRequest)
async def create_transport_request(
    request: TransportRequest,
    current_user: User = Depends(get_current_user)
):
    request.request_id = f"REQ-{len(transport_requests) + 1}"
    transport_requests.append(request.dict())
    return request

@app.get("/api/request", response_model=List[TransportRequest])
async def get_transport_requests():
    return transport_requests

@app.get("/api/request/{request_id}", response_model=TransportRequest)
async def get_transport_request(request_id: str):
    for request in transport_requests:
        if request["request_id"] == request_id:
            return request
    raise HTTPException(status_code=404, detail="Request not found")

@app.get("/api/find-truck")
async def find_trucks(current_user: User = Depends(get_current_user)):
    # Simulated truck data
    available_trucks = [
        {"id": "T1", "location": "City A", "capacity": 1000},
        {"id": "T2", "location": "City B", "capacity": 2000},
    ]
    return {"trucks": available_trucks}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
