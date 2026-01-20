from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Optional
import uvicorn

# 数据库设置
SQLALCHEMY_DATABASE_URL = "sqlite:///./email_simulation.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Pydantic 模型
class EmailBase(BaseModel):
    sender: Optional[str] = None
    recipient: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    timestamp: Optional[datetime] = None

class EmailCreate(EmailBase):
    pass

class EmailUpdate(BaseModel):
    read_status: Optional[bool] = None

class EmailFilter(BaseModel):
    recipient: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

# 数据库模型
class EmailDB(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)
    recipient = Column(String, index=True)
    subject = Column(String, index=True)
    body = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Simulated Email Backend", description="A sandbox email service for agent workflows")

# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 路由实现
@app.post("/send", response_model=dict)
def send_email(email: EmailCreate):
    """发送新邮件"""
    db = next(get_db())
    db_email = EmailDB(
        sender=email.sender,
        recipient=email.recipient,
        subject=email.subject,
        body=email.body,
        timestamp=email.timestamp or datetime.utcnow(),
        read=False
    )
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return {"message": "Email sent successfully", "id": db_email.id}


@app.get("/emails", response_model=List[dict])
def list_emails(skip: int = 0, limit: int = 100):
    """列出所有邮件"""
    db = next(get_db())
    emails = db.query(EmailDB).offset(skip).limit(limit).all()
    return [
        {
            "id": email.id,
            "sender": email.sender,
            "recipient": email.recipient,
            "subject": email.subject,
            "body": email.body,
            "timestamp": email.timestamp,
            "read": email.read
        }
        for email in emails
    ]


@app.get("/emails/unread", response_model=List[dict])
def list_unread_emails():
    """仅显示未读邮件"""
    db = next(get_db())
    emails = db.query(EmailDB).filter(EmailDB.read == False).all()
    return [
        {
            "id": email.id,
            "sender": email.sender,
            "recipient": email.recipient,
            "subject": email.subject,
            "body": email.body,
            "timestamp": email.timestamp,
            "read": email.read
        }
        for email in emails
    ]


@app.get("/emails/search", response_model=List[dict])
def search_emails(q: str = Query(..., min_length=1)):
    """按关键词搜索邮件"""
    db = next(get_db())
    emails = db.query(EmailDB).filter(
        (EmailDB.subject.contains(q)) | 
        (EmailDB.body.contains(q)) |
        (EmailDB.sender.contains(q))
    ).all()
    return [
        {
            "id": email.id,
            "sender": email.sender,
            "recipient": email.recipient,
            "subject": email.subject,
            "body": email.body,
            "timestamp": email.timestamp,
            "read": email.read
        }
        for email in emails
    ]


@app.get("/emails/filter", response_model=List[dict])
def filter_emails(recipient: Optional[str] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None):
    """按收件人或日期范围筛选"""
    db = next(get_db())
    query = db.query(EmailDB)
    
    if recipient:
        query = query.filter(EmailDB.recipient == recipient)
    if date_from:
        query = query.filter(EmailDB.timestamp >= date_from)
    if date_to:
        query = query.filter(EmailDB.timestamp <= date_to)
    
    emails = query.all()
    return [
        {
            "id": email.id,
            "sender": email.sender,
            "recipient": email.recipient,
            "subject": email.subject,
            "body": email.body,
            "timestamp": email.timestamp,
            "read": email.read
        }
        for email in emails
    ]


@app.get("/emails/{id}", response_model=dict)
def get_email(id: int):
    """按 ID 获取邮件"""
    db = next(get_db())
    email = db.query(EmailDB).filter(EmailDB.id == id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return {
        "id": email.id,
        "sender": email.sender,
        "recipient": email.recipient,
        "subject": email.subject,
        "body": email.body,
        "timestamp": email.timestamp,
        "read": email.read
    }


@app.patch("/emails/{id}/read", response_model=dict)
def mark_as_read(id: int):
    """将邮件标记为已读"""
    db = next(get_db())
    email = db.query(EmailDB).filter(EmailDB.id == id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email.read = True
    db.commit()
    return {"message": f"Email {id} marked as read"}


@app.patch("/emails/{id}/unread", response_model=dict)
def mark_as_unread(id: int):
    """将邮件标记为未读"""
    db = next(get_db())
    email = db.query(EmailDB).filter(EmailDB.id == id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email.read = False
    db.commit()
    return {"message": f"Email {id} marked as unread"}


@app.delete("/emails/{id}", response_model=dict)
def delete_email(id: int):
    """按 ID 删除邮件"""
    db = next(get_db())
    email = db.query(EmailDB).filter(EmailDB.id == id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    db.delete(email)
    db.commit()
    return {"message": f"Email {id} deleted successfully"}


@app.get("/reset_database", response_model=dict)
def reset_database():
    """重置到初始状态（用于测试）"""
    db = next(get_db())
    # 删除所有现有邮件
    db.query(EmailDB).delete()
    db.commit()
    
    # 添加一些默认邮件作为示例
    default_emails = [
        EmailDB(
            sender="manager@company.com",
            recipient="agent@company.com",
            subject="Weekly Report Due",
            body="Please submit your weekly report by Friday.",
            timestamp=datetime.utcnow(),
            read=False
        ),
        EmailDB(
            sender="hr@company.com",
            recipient="agent@company.com",
            subject="Team Meeting Reminder",
            body="Don't forget about our team meeting tomorrow at 10 AM.",
            timestamp=datetime.utcnow(),
            read=False
        ),
        EmailDB(
            sender="support@service.com",
            recipient="agent@company.com",
            subject="Customer Inquiry",
            body="A customer has raised an issue with our product. Please review and respond.",
            timestamp=datetime.utcnow(),
            read=True
        )
    ]
    
    for email in default_emails:
        db.add(email)
    
    db.commit()
    return {"message": "Database reset and initialized with sample emails"}


if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=5000)

