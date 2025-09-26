from fastapi import FastAPI, HTTPException, Depends, Request, Form, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mangum import Mangum
import os
import json
import boto3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Database Security Lab",
    description="Interactive Database Security Learning Platform",
    version="1.0.0"
)

# Security setup
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Templates setup
templates = Jinja2Templates(directory="templates")

# AWS setup
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# Table names
USERS_TABLE = os.getenv('USERS_TABLE', 'database-security-lab-users')
CONTENT_TABLE = os.getenv('CONTENT_TABLE', 'database-security-lab-content')
S3_BUCKET = os.getenv('S3_BUCKET', 'database-security-lab-assets')

# Pydantic models
class User(BaseModel):
    username: str
    email: str
    is_admin: bool = False
    is_active: bool = True

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ContentItem(BaseModel):
    id: str
    title: str
    content: str
    content_type: str  # 'exercise', 'step', 'reference'
    parent_id: Optional[str] = None
    order: int = 0
    is_hidden: bool = False
    created_at: datetime
    updated_at: datetime

class ContentCreate(BaseModel):
    title: str
    content: str
    content_type: str
    parent_id: Optional[str] = None
    order: int = 0
    is_hidden: bool = False

class ContentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    is_hidden: Optional[bool] = None

# Utility functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    # Get user from DynamoDB
    try:
        table = dynamodb.Table(USERS_TABLE)
        response = table.get_item(Key={'username': username})
        if 'Item' not in response:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**response['Item'])
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page showing the main exercise list"""
    try:
        # Get all exercises from DynamoDB
        table = dynamodb.Table(CONTENT_TABLE)
        response = table.scan(
            FilterExpression="content_type = :type AND attribute_not_exists(parent_id)",
            ExpressionAttributeValues={':type': 'exercise'}
        )
        exercises = sorted(response.get('Items', []), key=lambda x: x.get('order', 0))
        
        return templates.TemplateResponse("home.html", {
            "request": request,
            "exercises": exercises
        })
    except Exception as e:
        logger.error(f"Error loading home page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load exercises"
        })

@app.get("/exercise/{exercise_id}", response_class=HTMLResponse)
async def view_exercise(request: Request, exercise_id: str):
    """View a specific exercise with its steps"""
    try:
        table = dynamodb.Table(CONTENT_TABLE)
        
        # Get exercise
        exercise_response = table.get_item(Key={'id': exercise_id})
        if 'Item' not in exercise_response:
            raise HTTPException(status_code=404, detail="Exercise not found")
        
        exercise = exercise_response['Item']
        
        # Get steps for this exercise
        steps_response = table.scan(
            FilterExpression="content_type = :type AND parent_id = :parent",
            ExpressionAttributeValues={
                ':type': 'step',
                ':parent': exercise_id
            }
        )
        steps = sorted(steps_response.get('Items', []), key=lambda x: x.get('order', 0))
        
        return templates.TemplateResponse("exercise.html", {
            "request": request,
            "exercise": exercise,
            "steps": steps
        })
    except Exception as e:
        logger.error(f"Error loading exercise {exercise_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load exercise")

@app.get("/step/{step_id}", response_class=HTMLResponse)
async def view_step(request: Request, step_id: str):
    """View a specific step"""
    try:
        table = dynamodb.Table(CONTENT_TABLE)
        response = table.get_item(Key={'id': step_id})
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Step not found")
        
        step = response['Item']
        
        # Get parent exercise
        if step.get('parent_id'):
            parent_response = table.get_item(Key={'id': step['parent_id']})
            parent = parent_response.get('Item', {})
        else:
            parent = {}
        
        return templates.TemplateResponse("step.html", {
            "request": request,
            "step": step,
            "parent": parent
        })
    except Exception as e:
        logger.error(f"Error loading step {step_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load step")

# Authentication routes
@app.post("/auth/register")
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        table = dynamodb.Table(USERS_TABLE)
        
        # Check if user already exists
        response = table.get_item(Key={'username': user_data.username})
        if 'Item' in response:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user_item = {
            'username': user_data.username,
            'email': user_data.email,
            'hashed_password': hashed_password,
            'is_admin': False,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=user_item)
        
        return {"message": "User registered successfully"}
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login")
async def login(user_data: UserLogin):
    """Login user and return access token"""
    try:
        table = dynamodb.Table(USERS_TABLE)
        response = table.get_item(Key={'username': user_data.username})
        
        if 'Item' not in response:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = response['Item']
        if not verify_password(user_data.password, user['hashed_password']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not user.get('is_active', True):
            raise HTTPException(status_code=401, detail="Account is disabled")
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user['username']}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user['username'],
                "email": user['email'],
                "is_admin": user.get('is_admin', False)
            }
        }
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

# Admin routes for content management
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: User = Depends(get_admin_user)):
    """Admin dashboard for content management"""
    try:
        table = dynamodb.Table(CONTENT_TABLE)
        response = table.scan()
        content_items = response.get('Items', [])
        
        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "content_items": content_items,
            "user": current_user
        })
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")

@app.post("/api/content")
async def create_content(content: ContentCreate, current_user: User = Depends(get_admin_user)):
    """Create new content item"""
    try:
        table = dynamodb.Table(CONTENT_TABLE)
        
        # Generate unique ID
        content_id = f"{content.content_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        content_item = {
            'id': content_id,
            'title': content.title,
            'content': content.content,
            'content_type': content.content_type,
            'order': content.order,
            'is_hidden': content.is_hidden,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'created_by': current_user.username
        }
        
        if content.parent_id:
            content_item['parent_id'] = content.parent_id
        
        table.put_item(Item=content_item)
        
        return {"message": "Content created successfully", "id": content_id}
    except Exception as e:
        logger.error(f"Error creating content: {e}")
        raise HTTPException(status_code=500, detail="Failed to create content")

@app.put("/api/content/{content_id}")
async def update_content(content_id: str, content: ContentUpdate, current_user: User = Depends(get_admin_user)):
    """Update existing content item"""
    try:
        table = dynamodb.Table(CONTENT_TABLE)
        
        # Build update expression
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat()}
        
        if content.title is not None:
            update_expression += ", title = :title"
            expression_values[':title'] = content.title
        
        if content.content is not None:
            update_expression += ", content = :content"
            expression_values[':content'] = content.content
        
        if content.order is not None:
            update_expression += ", #order = :order"
            expression_values[':order'] = content.order
        
        if content.is_hidden is not None:
            update_expression += ", is_hidden = :is_hidden"
            expression_values[':is_hidden'] = content.is_hidden
        
        expression_attribute_names = {}
        if content.order is not None:
            expression_attribute_names['#order'] = 'order'
        
        kwargs = {
            'Key': {'id': content_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'UPDATED_NEW'
        }
        
        if expression_attribute_names:
            kwargs['ExpressionAttributeNames'] = expression_attribute_names
        
        table.update_item(**kwargs)
        
        return {"message": "Content updated successfully"}
    except Exception as e:
        logger.error(f"Error updating content {content_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update content")

@app.delete("/api/content/{content_id}")
async def delete_content(content_id: str, current_user: User = Depends(get_admin_user)):
    """Delete content item"""
    try:
        table = dynamodb.Table(CONTENT_TABLE)
        table.delete_item(Key={'id': content_id})
        
        return {"message": "Content deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting content {content_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete content")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_admin_user)):
    """Upload file to S3"""
    try:
        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        
        # Upload to S3
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET,
            filename,
            ExtraArgs={'ContentType': file.content_type}
        )
        
        # Generate public URL
        file_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"
        
        return {"message": "File uploaded successfully", "url": file_url}
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

# Additional API routes
@app.get("/api/exercise/{exercise_id}/steps")
async def get_exercise_steps(exercise_id: str):
    """Get all steps for an exercise"""
    try:
        table = dynamodb.Table(CONTENT_TABLE)
        response = table.scan(
            FilterExpression="content_type = :type AND parent_id = :parent",
            ExpressionAttributeValues={
                ':type': 'step',
                ':parent': exercise_id
            }
        )
        steps = sorted(response.get('Items', []), key=lambda x: x.get('order', 0))
        return steps
    except Exception as e:
        logger.error(f"Error getting steps for exercise {exercise_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get steps")

@app.post("/api/import-legacy")
async def import_legacy_content(current_user: User = Depends(get_admin_user)):
    """Import legacy HTML content"""
    try:
        # This would parse the existing HTML files and import them
        # For now, return a placeholder response
        return {"message": "Legacy import functionality will be implemented"}
    except Exception as e:
        logger.error(f"Error importing legacy content: {e}")
        raise HTTPException(status_code=500, detail="Failed to import legacy content")

@app.get("/api/export-content")
async def export_content(current_user: User = Depends(get_admin_user)):
    """Export all content as JSON"""
    try:
        table = dynamodb.Table(CONTENT_TABLE)
        response = table.scan()
        content_items = response.get('Items', [])
        
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'content_items': content_items
        }
        
        return JSONResponse(
            content=export_data,
            headers={
                'Content-Disposition': f'attachment; filename=database-security-lab-export-{datetime.utcnow().strftime("%Y%m%d")}.json'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting content: {e}")
        raise HTTPException(status_code=500, detail="Failed to export content")

@app.get("/auth/verify")
async def verify_token(current_user: User = Depends(get_current_user)):
    """Verify authentication token and return user info"""
    return current_user

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)