"""
Railway Backend for LogisticsManager
- FastAPI middleware between WPF and Supabase
- Telegram Bot for notifications and reports
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, Boolean, Numeric, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import NullPool
import httpx
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nkxnbvssbdtfniogcdfd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5reG5idnNzYmR0Zm5pb2djZGZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA0NDQxMDcsImV4cCI6MjA4NjAyMDEwN30.f9DIMzuer5ZGV4_74wqoO8szHYS_lykt5ZrNCuHgBcE")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "postgresql://postgres:Margsh2026x2@db.nkxnbvssbdtfniogcdfd.supabase.co:5432/postgres")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8568128078:AAEYfNy5RRdoSgSIA_QjnzzKbMdnB18tk60")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1119439099")  # @pepe116

# ==================== DATABASE MODELS ====================

Base = declarative_base()

class CloudOrder(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    local_id = Column(Integer, nullable=False)  # ID from WPF SQLite
    order_number = Column(String(50), nullable=False, unique=True)
    client_name = Column(String(200), nullable=False)
    container_count = Column(Integer, default=0)
    goods_type = Column(String(100))
    route = Column(String(200))
    transit_port = Column(String(100))
    document_number = Column(String(100))
    chinese_transport_company = Column(String(200))
    iranian_transport_company = Column(String(200))
    status = Column(String(50), default="New")
    status_color = Column(String(20), default="#FFFFFF")
    creation_date = Column(DateTime, default=datetime.utcnow)
    departure_date = Column(DateTime)
    arrival_iran_date = Column(DateTime)
    eta_date = Column(DateTime)
    arrival_notice_date = Column(DateTime)
    tkm_date = Column(DateTime)
    loading_date = Column(DateTime)
    truck_loading_date = Column(DateTime)
    arrival_turkmenistan_date = Column(DateTime)
    client_receiving_date = Column(DateTime)
    has_loading_photo = Column(Boolean, default=False)
    has_local_charges = Column(Boolean, default=False)
    has_tex = Column(Boolean, default=False)
    notes = Column(Text)
    additional_info = Column(Text)
    last_sync = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1)  # For conflict resolution
    
    containers = relationship("CloudContainer", back_populates="order", cascade="all, delete-orphan")
    tasks = relationship("CloudTask", back_populates="order", cascade="all, delete-orphan")

class CloudContainer(Base):
    __tablename__ = "containers"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    local_id = Column(Integer)  # ID from WPF SQLite
    container_number = Column(String(50))
    container_type = Column(String(50), default="20ft Standard")
    weight = Column(Numeric(10, 2), default=0)
    volume = Column(Numeric(10, 2), default=0)
    loading_date = Column(DateTime)
    departure_date = Column(DateTime)
    arrival_iran_date = Column(DateTime)
    truck_loading_date = Column(DateTime)
    arrival_turkmenistan_date = Column(DateTime)
    client_receiving_date = Column(DateTime)
    driver_first_name = Column(String(100))
    driver_last_name = Column(String(100))
    driver_company = Column(String(200))
    truck_number = Column(String(50))
    driver_iran_phone = Column(String(50))
    driver_turkmenistan_phone = Column(String(50))
    last_sync = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("CloudOrder", back_populates="containers")

class CloudTask(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    local_id = Column(Integer, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    description = Column(String(500), nullable=False)
    assigned_to = Column(String(100))
    status = Column(String(20), default="ToDo")  # ToDo, InProgress, Completed
    priority = Column(String(20), default="Medium")  # Low, Medium, High, Critical
    due_date = Column(DateTime)
    created_date = Column(DateTime, default=datetime.utcnow)
    last_sync = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("CloudOrder", back_populates="tasks")

class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String(100))  # Identifier for WPF installation
    sync_type = Column(String(20))  # "upload", "download", "conflict"
    records_synced = Column(Integer, default=0)
    status = Column(String(20))  # "success", "error", "partial"
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ==================== PYDANTIC MODELS ====================

class ContainerModel(BaseModel):
    id: Optional[int] = None
    container_number: Optional[str] = None
    container_type: str = "20ft Standard"
    weight: float = 0
    volume: float = 0
    loading_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    arrival_iran_date: Optional[datetime] = None
    truck_loading_date: Optional[datetime] = None
    arrival_turkmenistan_date: Optional[datetime] = None
    client_receiving_date: Optional[datetime] = None
    driver_first_name: Optional[str] = None
    driver_last_name: Optional[str] = None
    driver_company: Optional[str] = None
    truck_number: Optional[str] = None
    driver_iran_phone: Optional[str] = None
    driver_turkmenistan_phone: Optional[str] = None

class TaskModel(BaseModel):
    id: Optional[int] = None
    task_id: Optional[int] = None  # local_id
    order_id: int
    description: str
    assigned_to: Optional[str] = None
    status: str = "ToDo"
    priority: str = "Medium"
    due_date: Optional[datetime] = None
    created_date: Optional[datetime] = None

class OrderModel(BaseModel):
    id: Optional[int] = None
    order_number: str
    client_name: str
    container_count: int = 0
    goods_type: Optional[str] = None
    route: Optional[str] = None
    transit_port: Optional[str] = None
    document_number: Optional[str] = None
    chinese_transport_company: Optional[str] = None
    iranian_transport_company: Optional[str] = None
    status: str = "New"
    status_color: Optional[str] = "#FFFFFF"
    creation_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    arrival_iran_date: Optional[datetime] = None
    eta_date: Optional[datetime] = None
    arrival_notice_date: Optional[datetime] = None
    tkm_date: Optional[datetime] = None
    loading_date: Optional[datetime] = None
    truck_loading_date: Optional[datetime] = None
    arrival_turkmenistan_date: Optional[datetime] = None
    client_receiving_date: Optional[datetime] = None
    has_loading_photo: bool = False
    has_local_charges: bool = False
    has_tex: bool = False
    notes: Optional[str] = None
    additional_info: Optional[str] = None
    version: int = 1
    
    containers: List[ContainerModel] = []
    tasks: List[TaskModel] = []

class SyncRequest(BaseModel):
    device_id: str
    last_sync: Optional[datetime] = None
    orders: List[OrderModel] = []

class SyncResponse(BaseModel):
    success: bool
    message: str
    orders_uploaded: int = 0
    orders_downloaded: int = 0
    conflicts: List[Dict[str, Any]] = []
    server_time: datetime = Field(default_factory=datetime.utcnow)

class ReportRequest(BaseModel):
    report_type: str  # "daily", "weekly", "monthly", "all_active", "drivers"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    status_filter: Optional[List[str]] = None

# ==================== DATABASE SETUP ====================

engine = None
SessionLocal = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== TELEGRAM BOT ====================

telegram_app: Optional[Application] = None

async def start_telegram_bot():
    """Initialize and start Telegram bot"""
    global telegram_app
    
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your_telegram_token_here":
        logger.warning("Telegram token not configured, bot will not start")
        return
    
    try:
        telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        telegram_app.add_handler(CommandHandler("start", cmd_start))
        telegram_app.add_handler(CommandHandler("help", cmd_help))
        telegram_app.add_handler(CommandHandler("report", cmd_report))
        telegram_app.add_handler(CommandHandler("orders", cmd_orders))
        telegram_app.add_handler(CommandHandler("drivers", cmd_drivers))
        telegram_app.add_handler(CommandHandler("sync", cmd_sync_status))
        telegram_app.add_handler(CommandHandler("search", cmd_search))
        telegram_app.add_handler(CommandHandler("status", cmd_status_summary))
        
        # Start bot
        await telegram_app.initialize()
        await telegram_app.start()
        
        # Start polling in background
        asyncio.create_task(telegram_app.updater.start_polling())
        
        logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")

async def stop_telegram_bot():
    """Stop Telegram bot"""
    global telegram_app
    if telegram_app:
        await telegram_app.stop()
        logger.info("Telegram bot stopped")

# Telegram command handlers
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_text = """
🚛 *Margiana Logistics Reporting Bot*

Добро пожаловать! Я помогу отслеживать ваши грузы.

*Доступные команды:*
/report - Сводный отчет по заказам
/orders - Список активных заказов
/drivers - Список водителей
/status - Статус по направлениям
/search [номер] - Поиск заказа
/sync - Статус синхронизации
/help - Помощь

Данные обновляются автоматически при синхронизации с программой.
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = """
*Как использовать бота:*

1. *Отчеты* — используйте /report для получения текущей сводки
2. *Поиск* — /search ORD-001 найдет заказ по номеру
3. *Водители* — /drivers покажет всех водителей в пути
4. *Уведомления* — приходят автоматически при изменениях

*Статусы заказов:*
• New — Новый заказ
• In Progress CHN — В работе в Китае
• In Transit CHN-IR — В пути Китай-Иран
• In Progress IR — В работе в Иране
• In Transit IR-TKM — В пути Иран-Туркменистан
• Completed — Завершен
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send report"""
    try:
        db = SessionLocal()
        
        # Get statistics
        total_orders = db.query(CloudOrder).count()
        active_orders = db.query(CloudOrder).filter(
            CloudOrder.status.in_(["New", "In Progress CHN", "In Transit CHN-IR", 
                                  "In Progress IR", "In Transit IR-TKM"])
        ).count()
        
        # Status breakdown
        status_counts = {}
        for status in ["New", "In Progress CHN", "In Transit CHN-IR", 
                      "In Progress IR", "In Transit IR-TKM", "Completed"]:
            count = db.query(CloudOrder).filter(CloudOrder.status == status).count()
            if count > 0:
                status_counts[status] = count
        
        # Recent updates (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_syncs = db.query(SyncLog).filter(SyncLog.timestamp >= yesterday).count()
        
        # Container stats
        total_containers = db.query(CloudContainer).count()
        
        report = f"""
📊 *СВОДНЫЙ ОТЧЕТ — {datetime.now().strftime('%d.%m.%Y %H:%M')}*

*ОБЩАЯ СТАТИСТИКА:*
• Всего заказов: {total_orders}
• Активных: {active_orders}
• Контейнеров: {total_containers}

*ПО СТАТУСАМ:*
"""
        for status, count in status_counts.items():
            emoji = {
                "New": "🆕",
                "In Progress CHN": "🇨🇳",
                "In Transit CHN-IR": "🚢",
                "In Progress IR": "🇮🇷",
                "In Transit IR-TKM": "🚛",
                "Completed": "✅"
            }.get(status, "📋")
            report += f"• {emoji} {status}: {count}\n"
        
        report += f"""
*СИНХРОНИЗАЦИЯ:*
• Обновлений за 24ч: {recent_syncs}
• Последнее: {datetime.now().strftime('%H:%M')}

Используйте /orders для деталей по заказам.
        """
        
        await update.message.reply_text(report, parse_mode='Markdown')
        db.close()
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await update.message.reply_text("❌ Ошибка при генерации отчета")

async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active orders"""
    try:
        db = SessionLocal()
        
        orders = db.query(CloudOrder).filter(
            CloudOrder.status.in_(["New", "In Progress CHN", "In Transit CHN-IR", 
                                  "In Progress IR", "In Transit IR-TKM"])
        ).order_by(CloudOrder.creation_date.desc()).limit(10).all()
        
        if not orders:
            await update.message.reply_text("📭 Нет активных заказов")
            db.close()
            return
        
        message = "📋 *АКТИВНЫЕ ЗАКАЗЫ:*\n\n"
        
        for order in orders:
            emoji = {
                "New": "🆕",
                "In Progress CHN": "🇨🇳",
                "In Transit CHN-IR": "🚢",
                "In Progress IR": "🇮🇷",
                "In Transit IR-TKM": "🚛"
            }.get(order.status, "📋")
            
            containers = len(order.containers) if order.containers else order.container_count
            
            message += f"""{emoji} *{order.order_number}*
👤 {order.client_name}
🚛 {containers} конт. | {order.goods_type or '—'}
📍 {order.status}
📝 {order.notes[:50] if order.notes else '—'}

"""
        
        message += f"_Всего показано: {len(orders)} из {db.query(CloudOrder).filter(CloudOrder.status.in_(['New', 'In Progress CHN', 'In Transit CHN-IR', 'In Progress IR', 'In Transit IR-TKM'])).count()}_"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        db.close()
        
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка заказов")

async def cmd_drivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List drivers on the road"""
    try:
        db = SessionLocal()
        
        # Get containers with driver info that are in transit
        containers = db.query(CloudContainer).join(CloudOrder).filter(
            CloudContainer.driver_first_name != None,
            CloudOrder.status.in_(["In Transit CHN-IR", "In Transit IR-TKM", "In Progress IR"])
        ).all()
        
        if not containers:
            await update.message.reply_text("📭 Нет водителей в рейсе")
            db.close()
            return
        
        message = "🚛 *ВОДИТЕЛИ В РЕЙСЕ:*\n\n"
        
        for container in containers:
            pod_date = container.client_receiving_date.strftime('%d.%m') if container.client_receiving_date else "—"
            
            message += f"""👤 *{container.driver_first_name or ''} {container.driver_last_name or ''}*
🏢 {container.driver_company or '—'}
🚛 {container.truck_number or '—'} | {container.container_number or '—'}
📞 IR: {container.driver_iran_phone or '—'}
📞 TKM: {container.driver_turkmenistan_phone or '—'}
📦 Заказ: {container.order.order_number if container.order else '—'}
🎯 POD: {pod_date}

"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        db.close()
        
    except Exception as e:
        logger.error(f"Error listing drivers: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка водителей")

async def cmd_sync_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sync status"""
    try:
        db = SessionLocal()
        
        last_sync = db.query(SyncLog).order_by(SyncLog.timestamp.desc()).first()
        
        # Sync stats for last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        syncs_week = db.query(SyncLog).filter(SyncLog.timestamp >= week_ago).count()
        
        message = f"""
🔄 *СТАТУС СИНХРОНИЗАЦИИ*

*Последняя синхронизация:*
"""
        if last_sync:
            time_ago = datetime.utcnow() - last_sync.timestamp
            if time_ago < timedelta(minutes=1):
                time_str = "только что"
            elif time_ago < timedelta(hours=1):
                time_str = f"{int(time_ago.seconds / 60)} мин. назад"
            else:
                time_str = f"{int(time_ago.seconds / 3600)} ч. назад"
            
            message += f"""• Время: {last_sync.timestamp.strftime('%d.%m.%Y %H:%M')} ({time_str})
• Тип: {last_sync.sync_type}
• Записей: {last_sync.records_synced}
• Статус: {'✅' if last_sync.status == 'success' else '⚠️'} {last_sync.status}
"""
        else:
            message += "• Нет данных о синхронизации\n"
        
        message += f"""
*За последние 7 дней:* {syncs_week} синхронизаций

_Синхронизация происходит автоматически при работе программы._
        """
        
        await update.message.reply_text(message, parse_mode='Markdown')
        db.close()
        
    except Exception as e:
        logger.error(f"Error showing sync status: {e}")
        await update.message.reply_text("❌ Ошибка при получении статуса")

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for order"""
    if not context.args:
        await update.message.reply_text("🔍 Укажите номер заказа для поиска:\n/search ORD-001")
        return
    
    search_term = ' '.join(context.args)
    
    try:
        db = SessionLocal()
        
        orders = db.query(CloudOrder).filter(
            CloudOrder.order_number.ilike(f'%{search_term}%')
        ).all()
        
        if not orders:
            # Try searching by client name or container
            orders = db.query(CloudOrder).filter(
                CloudOrder.client_name.ilike(f'%{search_term}%')
            ).all()
        
        if not orders:
            await update.message.reply_text(f"🔍 Заказы по запросу '{search_term}' не найдены")
            db.close()
            return
        
        message = f"🔍 *РЕЗУЛЬТАТЫ ПОИСКА:* '{search_term}'\n\n"
        
        for order in orders:
            containers_info = ""
            if order.containers:
                for c in order.containers[:3]:  # Show max 3 containers
                    containers_info += f"  • {c.container_number or '—'}: {c.driver_first_name or ''} {c.driver_last_name or ''}\n"
            
            message += f"""📋 *{order.order_number}*
👤 {order.client_name}
📍 {order.status}
🚛 {order.container_count} конт. | {order.goods_type or '—'}
📝 {order.notes or '—'}

{containers_info}
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        db.close()
        
    except Exception as e:
        logger.error(f"Error searching: {e}")
        await update.message.reply_text("❌ Ошибка при поиске")

async def cmd_status_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show status summary by route"""
    try:
        db = SessionLocal()
        
        # Group by status and count
        status_data = {}
        for status in ["New", "In Progress CHN", "In Transit CHN-IR", 
                      "In Progress IR", "In Transit IR-TKM", "Completed", "Cancelled"]:
            count = db.query(CloudOrder).filter(CloudOrder.status == status).count()
            containers = db.query(CloudContainer).join(CloudOrder).filter(CloudOrder.status == status).count()
            status_data[status] = {"orders": count, "containers": containers}
        
        message = f"""
🗺 *СТАТУС ПО НАПРАВЛЕНИЯМ*

*Китай (отправление):*
🆕 Новые: {status_data['New']['orders']} заказов, {status_data['New']['containers']} конт.
🇨🇳 В работе: {status_data['In Progress CHN']['orders']} заказов, {status_data['In Progress CHN']['containers']} конт.

*В пути:*
🚢 Морем Китай-Иран: {status_data['In Transit CHN-IR']['orders']} заказов, {status_data['In Transit CHN-IR']['containers']} конт.

*Иран (транзит):*
🇮🇷 В работе: {status_data['In Progress IR']['orders']} заказов, {status_data['In Progress IR']['containers']} конт.
🚛 Авто Иран-ТКМ: {status_data['In Transit IR-TKM']['orders']} заказов, {status_data['In Transit IR-TKM']['containers']} конт.

*Завершено:*
✅ Completed: {status_data['Completed']['orders']} заказов
❌ Cancelled: {status_data['Cancelled']['orders']} заказов
        """
        
        await update.message.reply_text(message, parse_mode='Markdown')
        db.close()
        
    except Exception as e:
        logger.error(f"Error showing status summary: {e}")
        await update.message.reply_text("❌ Ошибка при получении сводки")

# Notification functions
async def notify_new_order(order: CloudOrder):
    """Send notification about new order"""
    if not telegram_app or not TELEGRAM_CHAT_ID:
        return
    
    try:
        message = f"""
🆕 *НОВЫЙ ЗАКАЗ СОЗДАН*

*{order.order_number}*
👤 {order.client_name}
🚛 {order.container_count} контейнеров
📦 {order.goods_type or '—'}
🛣 {order.route or '—'}

Создан: {order.creation_date.strftime('%d.%m.%Y %H:%M') if order.creation_date else '—'}
        """
        
        await telegram_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send new order notification: {e}")

async def notify_status_change(order: CloudOrder, old_status: str):
    """Send notification about status change"""
    if not telegram_app or not TELEGRAM_CHAT_ID:
        return
    
    try:
        message = f"""
📊 *ИЗМЕНЕНИЕ СТАТУСА*

*{order.order_number}*
👤 {order.client_name}

{old_status} → *{order.status}*

Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        """
        
        await telegram_app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send status change notification: {e}")

# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global engine, SessionLocal
    
    # Startup
    logger.info("Starting up...")
    
    # Initialize database
    try:
        engine = create_engine(
            SUPABASE_DB_URL,
            poolclass=NullPool,  # Required for serverless environment
            echo=False
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise
    
    # Start Telegram bot
    await start_telegram_bot()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await stop_telegram_bot()
    if engine:
        engine.dispose()

app = FastAPI(
    title="LogisticsManager Cloud API",
    description="Middleware for WPF-Supabase sync and Telegram notifications",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for WPF client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "LogisticsManager Cloud API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "telegram_bot": "running" if telegram_app else "not configured",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/sync", response_model=SyncResponse)
async def sync_data(request: SyncRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Main sync endpoint - WPF uploads data, receives updates"""
    try:
        logger.info(f"Sync request from device: {request.device_id}")
        
        uploaded = 0
        downloaded = 0
        conflicts = []
        
        # Process uploaded orders
        for order_data in request.orders:
            try:
                # Check if order exists
                existing = db.query(CloudOrder).filter(
                    CloudOrder.order_number == order_data.order_number
                ).first()
                
                if existing:
                    # Conflict detection: compare versions
                    if order_data.version < existing.version:
                        # WPF has older version, don't overwrite
                        conflicts.append({
                            "order_number": order_data.order_number,
                            "type": "server_newer",
                            "server_version": existing.version,
                            "client_version": order_data.version
                        })
                        downloaded += 1
                        continue
                    
                    # Update existing
                    existing.client_name = order_data.client_name
                    existing.container_count = order_data.container_count
                    existing.goods_type = order_data.goods_type
                    existing.route = order_data.route
                    existing.transit_port = order_data.transit_port
                    existing.document_number = order_data.document_number
                    existing.chinese_transport_company = order_data.chinese_transport_company
                    existing.iranian_transport_company = order_data.iranian_transport_company
                    existing.status = order_data.status
                    existing.status_color = order_data.status_color
                    existing.departure_date = order_data.departure_date
                    existing.arrival_iran_date = order_data.arrival_iran_date
                    existing.eta_date = order_data.eta_date
                    existing.arrival_notice_date = order_data.arrival_notice_date
                    existing.tkm_date = order_data.tkm_date
                    existing.loading_date = order_data.loading_date
                    existing.truck_loading_date = order_data.truck_loading_date
                    existing.arrival_turkmenistan_date = order_data.arrival_turkmenistan_date
                    existing.client_receiving_date = order_data.client_receiving_date
                    existing.has_loading_photo = order_data.has_loading_photo
                    existing.has_local_charges = order_data.has_local_charges
                    existing.has_tex = order_data.has_tex
                    existing.notes = order_data.notes
                    existing.additional_info = order_data.additional_info
                    existing.version = order_data.version + 1
                    existing.last_sync = datetime.utcnow()
                    
                    # Clear and recreate containers
                    db.query(CloudContainer).filter(CloudContainer.order_id == existing.id).delete()
                    for container_data in order_data.containers:
                        container = CloudContainer(
                            order_id=existing.id,
                            local_id=container_data.id,
                            container_number=container_data.container_number,
                            container_type=container_data.container_type,
                            weight=container_data.weight,
                            volume=container_data.volume,
                            loading_date=container_data.loading_date,
                            departure_date=container_data.departure_date,
                            arrival_iran_date=container_data.arrival_iran_date,
                            truck_loading_date=container_data.truck_loading_date,
                            arrival_turkmenistan_date=container_data.arrival_turkmenistan_date,
                            client_receiving_date=container_data.client_receiving_date,
                            driver_first_name=container_data.driver_first_name,
                            driver_last_name=container_data.driver_last_name,
                            driver_company=container_data.driver_company,
                            truck_number=container_data.truck_number,
                            driver_iran_phone=container_data.driver_iran_phone,
                            driver_turkmenistan_phone=container_data.driver_turkmenistan_phone,
                            last_sync=datetime.utcnow()
                        )
                        db.add(container)
                    
                    # Clear and recreate tasks
                    db.query(CloudTask).filter(CloudTask.order_id == existing.id).delete()
                    for task_data in order_data.tasks:
                        task = CloudTask(
                            order_id=existing.id,
                            local_id=task_data.task_id,
                            description=task_data.description,
                            assigned_to=task_data.assigned_to,
                            status=task_data.status,
                            priority=task_data.priority,
                            due_date=task_data.due_date,
                            created_date=task_data.created_date,
                            last_sync=datetime.utcnow()
                        )
                        db.add(task)
                    
                    uploaded += 1
                    
                else:
                    # Create new order
                    new_order = CloudOrder(
                        local_id=order_data.id or 0,
                        order_number=order_data.order_number,
                        client_name=order_data.client_name,
                        container_count=order_data.container_count,
                        goods_type=order_data.goods_type,
                        route=order_data.route,
                        transit_port=order_data.transit_port,
                        document_number=order_data.document_number,
                        chinese_transport_company=order_data.chinese_transport_company,
                        iranian_transport_company=order_data.iranian_transport_company,
                        status=order_data.status,
                        status_color=order_data.status_color,
                        creation_date=order_data.creation_date or datetime.utcnow(),
                        departure_date=order_data.departure_date,
                        arrival_iran_date=order_data.arrival_iran_date,
                        eta_date=order_data.eta_date,
                        arrival_notice_date=order_data.arrival_notice_date,
                        tkm_date=order_data.tkm_date,
                        loading_date=order_data.loading_date,
                        truck_loading_date=order_data.truck_loading_date,
                        arrival_turkmenistan_date=order_data.arrival_turkmenistan_date,
                        client_receiving_date=order_data.client_receiving_date,
                        has_loading_photo=order_data.has_loading_photo,
                        has_local_charges=order_data.has_local_charges,
                        has_tex=order_data.has_tex,
                        notes=order_data.notes,
                        additional_info=order_data.additional_info,
                        version=1,
                        last_sync=datetime.utcnow()
                    )
                    db.add(new_order)
                    db.flush()  # Get the ID
                    
                    # Add containers
                    for container_data in order_data.containers:
                        container = CloudContainer(
                            order_id=new_order.id,
                            local_id=container_data.id,
                            container_number=container_data.container_number,
                            container_type=container_data.container_type,
                            weight=container_data.weight,
                            volume=container_data.volume,
                            loading_date=container_data.loading_date,
                            departure_date=container_data.departure_date,
                            arrival_iran_date=container_data.arrival_iran_date,
                            truck_loading_date=container_data.truck_loading_date,
                            arrival_turkmenistan_date=container_data.arrival_turkmenistan_date,
                            client_receiving_date=container_data.client_receiving_date,
                            driver_first_name=container_data.driver_first_name,
                            driver_last_name=container_data.driver_last_name,
                            driver_company=container_data.driver_company,
                            truck_number=container_data.truck_number,
                            driver_iran_phone=container_data.driver_iran_phone,
                            driver_turkmenistan_phone=container_data.driver_turkmenistan_phone,
                            last_sync=datetime.utcnow()
                        )
                        db.add(container)
                    
                    # Add tasks
                    for task_data in order_data.tasks:
                        task = CloudTask(
                            order_id=new_order.id,
                            local_id=task_data.task_id,
                            description=task_data.description,
                            assigned_to=task_data.assigned_to,
                            status=task_data.status,
                            priority=task_data.priority,
                            due_date=task_data.due_date,
                            created_date=task_data.created_date or datetime.utcnow(),
                            last_sync=datetime.utcnow()
                        )
                        db.add(task)
                    
                    uploaded += 1
                    
                    # Notify about new order
                    background_tasks.add_task(notify_new_order, new_order)
                
            except Exception as e:
                logger.error(f"Error processing order {order_data.order_number}: {e}")
                conflicts.append({
                    "order_number": order_data.order_number,
                    "type": "error",
                    "message": str(e)
                })
        
        # Commit all changes
        db.commit()
        
        # Log sync
        sync_log = SyncLog(
            device_id=request.device_id,
            sync_type="upload",
            records_synced=uploaded,
            status="success" if not conflicts else "partial",
            message=f"Uploaded {uploaded} orders, {len(conflicts)} conflicts"
        )
        db.add(sync_log)
        db.commit()
        
        logger.info(f"Sync completed: {uploaded} uploaded, {downloaded} conflicts")
        
        return SyncResponse(
            success=True,
            message=f"Synchronized successfully. Uploaded: {uploaded}, Conflicts: {len(conflicts)}",
            orders_uploaded=uploaded,
            orders_downloaded=downloaded,
            conflicts=conflicts
        )
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
        
        # Log failed sync
        try:
            sync_log = SyncLog(
                device_id=request.device_id,
                sync_type="upload",
                records_synced=0,
                status="error",
                message=str(e)
            )
            db.add(sync_log)
            db.commit()
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@app.get("/sync/download")
async def download_data(device_id: str, last_sync: Optional[datetime] = None, db: Session = Depends(get_db)):
    """Download data from cloud - for WPF to get updates"""
    try:
        query = db.query(CloudOrder)
        
        if last_sync:
            query = query.filter(CloudOrder.last_sync > last_sync)
        
        orders = query.order_by(CloudOrder.last_sync.desc()).limit(100).all()
        
        result = []
        for order in orders:
            order_dict = {
                "id": order.local_id,
                "order_number": order.order_number,
                "client_name": order.client_name,
                "container_count": order.container_count,
                "goods_type": order.goods_type,
                "route": order.route,
                "transit_port": order.transit_port,
                "document_number": order.document_number,
                "chinese_transport_company": order.chinese_transport_company,
                "iranian_transport_company": order.iranian_transport_company,
                "status": order.status,
                "status_color": order.status_color,
                "creation_date": order.creation_date.isoformat() if order.creation_date else None,
                "departure_date": order.departure_date.isoformat() if order.departure_date else None,
                "arrival_iran_date": order.arrival_iran_date.isoformat() if order.arrival_iran_date else None,
                "eta_date": order.eta_date.isoformat() if order.eta_date else None,
                "arrival_notice_date": order.arrival_notice_date.isoformat() if order.arrival_notice_date else None,
                "tkm_date": order.tkm_date.isoformat() if order.tkm_date else None,
                "loading_date": order.loading_date.isoformat() if order.loading_date else None,
                "truck_loading_date": order.truck_loading_date.isoformat() if order.truck_loading_date else None,
                "arrival_turkmenistan_date": order.arrival_turkmenistan_date.isoformat() if order.arrival_turkmenistan_date else None,
                "client_receiving_date": order.client_receiving_date.isoformat() if order.client_receiving_date else None,
                "has_loading_photo": order.has_loading_photo,
                "has_local_charges": order.has_local_charges,
                "has_tex": order.has_tex,
                "notes": order.notes,
                "additional_info": order.additional_info,
                "version": order.version,
                "last_sync": order.last_sync.isoformat() if order.last_sync else None,
                "containers": [],
                "tasks": []
            }
            
            for container in order.containers:
                order_dict["containers"].append({
                    "id": container.local_id,
                    "container_number": container.container_number,
                    "container_type": container.container_type,
                    "weight": float(container.weight) if container.weight else 0,
                    "volume": float(container.volume) if container.volume else 0,
                    "loading_date": container.loading_date.isoformat() if container.loading_date else None,
                    "departure_date": container.departure_date.isoformat() if container.departure_date else None,
                    "arrival_iran_date": container.arrival_iran_date.isoformat() if container.arrival_iran_date else None,
                    "truck_loading_date": container.truck_loading_date.isoformat() if container.truck_loading_date else None,
                    "arrival_turkmenistan_date": container.arrival_turkmenistan_date.isoformat() if container.arrival_turkmenistan_date else None,
                    "client_receiving_date": container.client_receiving_date.isoformat() if container.client_receiving_date else None,
                    "driver_first_name": container.driver_first_name,
                    "driver_last_name": container.driver_last_name,
                    "driver_company": container.driver_company,
                    "truck_number": container.truck_number,
                    "driver_iran_phone": container.driver_iran_phone,
                    "driver_turkmenistan_phone": container.driver_turkmenistan_phone
                })
            
            for task in order.tasks:
                order_dict["tasks"].append({
                    "task_id": task.local_id,
                    "order_id": order.local_id,
                    "description": task.description,
                    "assigned_to": task.assigned_to,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "created_date": task.created_date.isoformat() if task.created_date else None
                })
            
            result.append(order_dict)
        
        return {
            "success": True,
            "orders": result,
            "count": len(result),
            "server_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/report")
async def generate_report(request: ReportRequest, db: Session = Depends(get_db)):
    """Generate report - can be called by WPF or scheduled"""
    try:
        query = db.query(CloudOrder)
        
        if request.status_filter:
            query = query.filter(CloudOrder.status.in_(request.status_filter))
        
        if request.date_from:
            query = query.filter(CloudOrder.creation_date >= request.date_from)
        
        if request.date_to:
            query = query.filter(CloudOrder.creation_date <= request.date_to)
        
        orders = query.all()
        
        # Calculate statistics
        stats = {
            "total_orders": len(orders),
            "total_containers": sum(o.container_count for o in orders),
            "by_status": {},
            "total_weight": 0
        }
        
        for order in orders:
            if order.status not in stats["by_status"]:
                stats["by_status"][order.status] = 0
            stats["by_status"][order.status] += 1
            
            for container in order.containers:
                stats["total_weight"] += float(container.weight) if container.weight else 0
        
        return {
            "success": True,
            "report_type": request.report_type,
            "statistics": stats,
            "orders": [
                {
                    "order_number": o.order_number,
                    "client_name": o.client_name,
                    "status": o.status,
                    "container_count": o.container_count,
                    "creation_date": o.creation_date.isoformat() if o.creation_date else None
                }
                for o in orders[:50]  # Limit details
            ],
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Report failed: {str(e)}")

@app.get("/drivers")
async def get_drivers(status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get drivers information"""
    try:
        query = db.query(CloudContainer).join(CloudOrder)
        
        if status:
            query = query.filter(CloudOrder.status == status)
        
        containers = query.filter(
            CloudContainer.driver_first_name != None
        ).all()
        
        drivers = []
        for container in containers:
            drivers.append({
                "first_name": container.driver_first_name,
                "last_name": container.driver_last_name,
                "company": container.driver_company,
                "truck_number": container.truck_number,
                "iran_phone": container.driver_iran_phone,
                "turkmenistan_phone": container.driver_turkmenistan_phone,
                "container_number": container.container_number,
                "order_number": container.order.order_number if container.order else None,
                "order_status": container.order.status if container.order else None
            })
        
        return {
            "success": True,
            "count": len(drivers),
            "drivers": drivers
        }
        
    except Exception as e:
        logger.error(f"Drivers query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

# Webhook endpoint for Railway cron jobs
@app.post("/webhook/scheduled-report")
async def scheduled_report(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Endpoint for Railway cron job to trigger daily reports"""
    try:
        # Generate daily report
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        new_orders = db.query(CloudOrder).filter(
            CloudOrder.creation_date >= yesterday
        ).count()
        
        status_changes = db.query(SyncLog).filter(
            SyncLog.timestamp >= yesterday,
            SyncLog.sync_type == "upload"
        ).count()
        
        # Send to Telegram
        if telegram_app and TELEGRAM_CHAT_ID:
            message = f"""
📊 *ЕЖЕДНЕВНЫЙ ОТЧЕТ*

*{datetime.now().strftime('%d.%m.%Y')}*

*Новые заказы:* {new_orders}
*Обновлений:* {status_changes}

Используйте /report для деталей.
            """
            
            background_tasks.add_task(
                telegram_app.bot.send_message,
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='Markdown'
            )
        
        return {"success": True, "new_orders": new_orders, "updates": status_changes}
        
    except Exception as e:
        logger.error(f"Scheduled report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))