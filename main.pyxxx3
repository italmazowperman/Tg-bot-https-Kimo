"""
Railway Backend for LogisticsManager - РАБОЧАЯ ВЕРСИЯ
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, Boolean, Numeric, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import NullPool
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# Получаем DATABASE_URL из переменных окружения Railway
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL", "")

# Используем публичный URL если доступен, иначе обычный
if DATABASE_PUBLIC_URL and "railway" in DATABASE_PUBLIC_URL:
    DATABASE_URL = DATABASE_PUBLIC_URL
    logger.info("Using DATABASE_PUBLIC_URL")

# Очистка URL от пробелов
DATABASE_URL = DATABASE_URL.strip() if DATABASE_URL else ""

if not DATABASE_URL:
    # Fallback для локального тестирования (замените на ваш реальный публичный URL)
    DATABASE_URL = "postgresql://postgres:ZMhXQDvRXVJFDfoAvccbEndHRbKheqXM@shuttle.proxy.rlwy.net:41263/railway"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8568128078:AAEYfNy5RRdoSgSIA_QjnzzKbMdnB18tk60")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1119439099")

# Убираем пробелы из токена
TELEGRAM_TOKEN = TELEGRAM_TOKEN.strip() if TELEGRAM_TOKEN else ""

logger.info(f"Database URL configured: {bool(DATABASE_URL)}")
logger.info(f"Telegram token configured: {bool(TELEGRAM_TOKEN and len(TELEGRAM_TOKEN) > 20)}")

# ==================== PYDANTIC MODELS ====================

class ContainerModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    Id: Optional[int] = Field(None, alias="id")
    ContainerNumber: Optional[str] = Field(None, alias="container_number")
    ContainerType: str = Field("20ft Standard", alias="container_type")
    Weight: float = Field(0, alias="weight")
    Volume: float = Field(0, alias="volume")
    LoadingDate: Optional[datetime] = Field(None, alias="loading_date")
    DepartureDate: Optional[datetime] = Field(None, alias="departure_date")
    ArrivalIranDate: Optional[datetime] = Field(None, alias="arrival_iran_date")
    TruckLoadingDate: Optional[datetime] = Field(None, alias="truck_loading_date")
    ArrivalTurkmenistanDate: Optional[datetime] = Field(None, alias="arrival_turkmenistan_date")
    ClientReceivingDate: Optional[datetime] = Field(None, alias="client_receiving_date")
    DriverFirstName: Optional[str] = Field(None, alias="driver_first_name")
    DriverLastName: Optional[str] = Field(None, alias="driver_last_name")
    DriverCompany: Optional[str] = Field(None, alias="driver_company")
    TruckNumber: Optional[str] = Field(None, alias="truck_number")
    DriverIranPhone: Optional[str] = Field(None, alias="driver_iran_phone")
    DriverTurkmenistanPhone: Optional[str] = Field(None, alias="driver_turkmenistan_phone")

class TaskModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    TaskId: Optional[int] = Field(None, alias="task_id")
    OrderId: int = Field(alias="order_id")
    Description: str = Field(alias="description")
    AssignedTo: Optional[str] = Field(None, alias="assigned_to")
    Status: str = Field("ToDo", alias="status")
    Priority: str = Field("Medium", alias="priority")
    DueDate: Optional[datetime] = Field(None, alias="due_date")
    CreatedDate: Optional[datetime] = Field(None, alias="created_date")

class OrderModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    Id: Optional[int] = Field(None, alias="id")
    OrderNumber: str = Field(alias="order_number")
    ClientName: str = Field(alias="client_name")
    ContainerCount: int = Field(0, alias="container_count")
    GoodsType: Optional[str] = Field(None, alias="goods_type")
    Route: Optional[str] = Field(None, alias="route")
    TransitPort: Optional[str] = Field(None, alias="transit_port")
    DocumentNumber: Optional[str] = Field(None, alias="document_number")
    ChineseTransportCompany: Optional[str] = Field(None, alias="chinese_transport_company")
    IranianTransportCompany: Optional[str] = Field(None, alias="iranian_transport_company")
    Status: str = Field("New", alias="status")
    StatusColor: Optional[str] = Field("#FFFFFF", alias="status_color")
    CreationDate: Optional[datetime] = Field(None, alias="creation_date")
    DepartureDate: Optional[datetime] = Field(None, alias="departure_date")
    ArrivalIranDate: Optional[datetime] = Field(None, alias="arrival_iran_date")
    EtaDate: Optional[datetime] = Field(None, alias="eta_date")
    ArrivalNoticeDate: Optional[datetime] = Field(None, alias="arrival_notice_date")
    TkmDate: Optional[datetime] = Field(None, alias="tkm_date")
    LoadingDate: Optional[datetime] = Field(None, alias="loading_date")
    TruckLoadingDate: Optional[datetime] = Field(None, alias="truck_loading_date")
    ArrivalTurkmenistanDate: Optional[datetime] = Field(None, alias="arrival_turkmenistan_date")
    ClientReceivingDate: Optional[datetime] = Field(None, alias="client_receiving_date")
    HasLoadingPhoto: bool = Field(False, alias="has_loading_photo")
    HasLocalCharges: bool = Field(False, alias="has_local_charges")
    HasTex: bool = Field(False, alias="has_tex")
    Notes: Optional[str] = Field(None, alias="notes")
    AdditionalInfo: Optional[str] = Field(None, alias="additional_info")
    Version: int = Field(1, alias="version")
    
    Containers: List[ContainerModel] = Field([], alias="containers")
    Tasks: List[TaskModel] = Field([], alias="tasks")

class SyncRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    DeviceId: str = Field(alias="device_id")
    LastSync: Optional[datetime] = Field(None, alias="last_sync")
    Orders: List[OrderModel] = Field([], alias="orders")

class SyncResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    Success: bool = Field(alias="success")
    Message: str = Field(alias="message")
    OrdersUploaded: int = Field(0, alias="orders_uploaded")
    OrdersDownloaded: int = Field(0, alias="orders_downloaded")
    Conflicts: List[Dict[str, Any]] = Field([], alias="conflicts")
    ServerTime: datetime = Field(default_factory=datetime.utcnow, alias="server_time")

# ==================== DATABASE MODELS ====================

Base = declarative_base()

class CloudOrder(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    local_id = Column(Integer, nullable=False, index=True)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    client_name = Column(String(200), nullable=False)
    container_count = Column(Integer, default=0)
    goods_type = Column(String(100))
    route = Column(String(200))
    transit_port = Column(String(100))
    document_number = Column(String(100))
    chinese_transport_company = Column(String(200))
    iranian_transport_company = Column(String(200))
    status = Column(String(50), default="New", index=True)
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
    last_sync = Column(DateTime, default=datetime.utcnow, index=True)
    version = Column(Integer, default=1)
    device_id = Column(String(100), index=True)
    
    containers = relationship("CloudContainer", back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    tasks = relationship("CloudTask", back_populates="order", cascade="all, delete-orphan", lazy="selectin")

class CloudContainer(Base):
    __tablename__ = "containers"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    local_id = Column(Integer)
    container_number = Column(String(50), index=True)
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
    local_id = Column(Integer, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    assigned_to = Column(String(100))
    status = Column(String(20), default="ToDo", index=True)
    priority = Column(String(20), default="Medium")
    due_date = Column(DateTime)
    created_date = Column(DateTime, default=datetime.utcnow)
    last_sync = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("CloudOrder", back_populates="tasks")

class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String(100), index=True)
    sync_type = Column(String(20))
    records_synced = Column(Integer, default=0)
    status = Column(String(20))
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

# ==================== GLOBALS ====================

engine = None
SessionLocal = None
telegram_app: Optional[Application] = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== TELEGRAM BOT ====================

async def start_telegram_bot():
    global telegram_app
    
    if not TELEGRAM_TOKEN or len(TELEGRAM_TOKEN) < 20:
        logger.warning("Telegram token not configured properly, bot will not start")
        return
    
    try:
        telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        telegram_app.add_handler(CommandHandler("start", cmd_start))
        telegram_app.add_handler(CommandHandler("help", cmd_help))
        telegram_app.add_handler(CommandHandler("report", cmd_report))
        telegram_app.add_handler(CommandHandler("orders", cmd_orders))
        telegram_app.add_handler(CommandHandler("drivers", cmd_drivers))
        telegram_app.add_handler(CommandHandler("sync", cmd_sync_status))
        telegram_app.add_handler(CommandHandler("search", cmd_search))
        telegram_app.add_handler(CommandHandler("status", cmd_status_summary))
        
        await telegram_app.initialize()
        await telegram_app.start()
        
        # Удаляем webhook перед polling
        await telegram_app.bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем polling в отдельной задаче
        asyncio.create_task(run_polling())
        
        logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")

async def run_polling():
    """Запуск polling в отдельной задаче с обработкой ошибок"""
    try:
        await telegram_app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"Polling error: {e}")

async def stop_telegram_bot():
    global telegram_app
    if telegram_app:
        try:
            await telegram_app.updater.stop()
            await telegram_app.stop()
            logger.info("Telegram bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    if not SessionLocal:
        await update.message.reply_text("❌ База данных недоступна")
        return
    
    db = SessionLocal()
    try:
        total_orders = db.query(CloudOrder).count()
        active_orders = db.query(CloudOrder).filter(
            CloudOrder.status.in_(["New", "In Progress CHN", "In Transit CHN-IR", 
                                  "In Progress IR", "In Transit IR-TKM"])
        ).count()
        
        status_counts = {}
        for status in ["New", "In Progress CHN", "In Transit CHN-IR", 
                      "In Progress IR", "In Transit IR-TKM", "Completed"]:
            count = db.query(CloudOrder).filter(CloudOrder.status == status).count()
            if count > 0:
                status_counts[status] = count
        
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_syncs = db.query(SyncLog).filter(SyncLog.timestamp >= yesterday).count()
        
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
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await update.message.reply_text("❌ Ошибка при генерации отчета")
    finally:
        db.close()

async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not SessionLocal:
        await update.message.reply_text("❌ База данных недоступна")
        return
    
    db = SessionLocal()
    try:
        orders = db.query(CloudOrder).filter(
            CloudOrder.status.in_(["New", "In Progress CHN", "In Transit CHN-IR", 
                                  "In Progress IR", "In Transit IR-TKM"])
        ).order_by(CloudOrder.creation_date.desc()).limit(10).all()
        
        if not orders:
            await update.message.reply_text("📭 Нет активных заказов")
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
        
        message += f"_Всего показано: {len(orders)}_"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка заказов")
    finally:
        db.close()

async def cmd_drivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not SessionLocal:
        await update.message.reply_text("❌ База данных недоступна")
        return
    
    db = SessionLocal()
    try:
        containers = db.query(CloudContainer).join(CloudOrder).filter(
            CloudContainer.driver_first_name != None,
            CloudOrder.status.in_(["In Transit CHN-IR", "In Transit IR-TKM", "In Progress IR"])
        ).limit(20).all()
        
        if not containers:
            await update.message.reply_text("📭 Нет водителей в рейсе")
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
        
    except Exception as e:
        logger.error(f"Error listing drivers: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка водителей")
    finally:
        db.close()

async def cmd_sync_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not SessionLocal:
        await update.message.reply_text("❌ База данных недоступна")
        return
    
    db = SessionLocal()
    try:
        last_sync = db.query(SyncLog).order_by(SyncLog.timestamp.desc()).first()
        
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
        
    except Exception as e:
        logger.error(f"Error showing sync status: {e}")
        await update.message.reply_text("❌ Ошибка при получении статуса")
    finally:
        db.close()

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 Укажите номер заказа для поиска:\n/search ORD-001")
        return
    
    if not SessionLocal:
        await update.message.reply_text("❌ База данных недоступна")
        return
    
    search_term = ' '.join(context.args)
    db = SessionLocal()
    
    try:
        orders = db.query(CloudOrder).filter(
            CloudOrder.order_number.ilike(f'%{search_term}%')
        ).limit(5).all()
        
        if not orders:
            orders = db.query(CloudOrder).filter(
                CloudOrder.client_name.ilike(f'%{search_term}%')
            ).limit(5).all()
        
        if not orders:
            await update.message.reply_text(f"🔍 Заказы по запросу '{search_term}' не найдены")
            return
        
        message = f"🔍 *РЕЗУЛЬТАТЫ ПОИСКА:* '{search_term}'\n\n"
        
        for order in orders:
            containers_info = ""
            if order.containers:
                for c in order.containers[:3]:
                    containers_info += f"  • {c.container_number or '—'}: {c.driver_first_name or ''} {c.driver_last_name or ''}\n"
            
            message += f"""📋 *{order.order_number}*
👤 {order.client_name}
📍 {order.status}
🚛 {order.container_count} конт. | {order.goods_type or '—'}
📝 {order.notes or '—'}

{containers_info}
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error searching: {e}")
        await update.message.reply_text("❌ Ошибка при поиске")
    finally:
        db.close()

async def cmd_status_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not SessionLocal:
        await update.message.reply_text("❌ База данных недоступна")
        return
    
    db = SessionLocal()
    try:
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
        
    except Exception as e:
        logger.error(f"Error showing status summary: {e}")
        await update.message.reply_text("❌ Ошибка при получении сводки")
    finally:
        db.close()

async def notify_new_order(order: CloudOrder):
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
    global engine, SessionLocal
    
    logger.info("=" * 50)
    logger.info("Starting LogisticsManager API...")
    logger.info("=" * 50)
    
    # Initialize database
    try:
        logger.info(f"Connecting to database...")
        
        # Используем более надежные параметры подключения
        connect_args = {
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
        
        engine = create_engine(
            DATABASE_URL,
            poolclass=NullPool,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args
        )
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Test connection with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    logger.info(f"Database connection test: {result.scalar()}")
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(2)
                else:
                    raise
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        # Don't raise - let the app start without database
        # Telegram bot can still work
    
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
    description="Middleware for WPF-Railway PostgreSQL sync and Telegram notifications",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for WPF client - РАЗРЕШАЕМ ВСЁ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    db_status = "unknown"
    try:
        if engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "service": "LogisticsManager Cloud API",
        "version": "1.0.0",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    try:
        if engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        else:
            db_status = "not_initialized"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "telegram_bot": "running" if telegram_app else "not_configured",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/sync", response_model=SyncResponse)
async def sync_data(request: SyncRequest, background_tasks: BackgroundTasks):
    """Main sync endpoint - WPF uploads data"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = SessionLocal()
    try:
        logger.info(f"Sync request from device: {request.DeviceId}, orders: {len(request.Orders)}")
        
        uploaded = 0
        downloaded = 0
        conflicts = []
        
        for order_data in request.Orders:
            try:
                # Check if order exists
                existing = db.query(CloudOrder).filter(
                    CloudOrder.order_number == order_data.OrderNumber
                ).first()
                
                if existing:
                    # Conflict detection
                    if order_data.Version < existing.version:
                        conflicts.append({
                            "order_number": order_data.OrderNumber,
                            "type": "server_newer",
                            "server_version": existing.version,
                            "client_version": order_data.Version
                        })
                        downloaded += 1
                        continue
                    
                    old_status = existing.status
                    
                    # Update existing order
                    existing.client_name = order_data.ClientName
                    existing.container_count = order_data.ContainerCount
                    existing.goods_type = order_data.GoodsType
                    existing.route = order_data.Route
                    existing.transit_port = order_data.TransitPort
                    existing.document_number = order_data.DocumentNumber
                    existing.chinese_transport_company = order_data.ChineseTransportCompany
                    existing.iranian_transport_company = order_data.IranianTransportCompany
                    existing.status = order_data.Status
                    existing.status_color = order_data.StatusColor
                    existing.departure_date = order_data.DepartureDate
                    existing.arrival_iran_date = order_data.ArrivalIranDate
                    existing.eta_date = order_data.EtaDate
                    existing.arrival_notice_date = order_data.ArrivalNoticeDate
                    existing.tkm_date = order_data.TkmDate
                    existing.loading_date = order_data.LoadingDate
                    existing.truck_loading_date = order_data.TruckLoadingDate
                    existing.arrival_turkmenistan_date = order_data.ArrivalTurkmenistanDate
                    existing.client_receiving_date = order_data.ClientReceivingDate
                    existing.has_loading_photo = order_data.HasLoadingPhoto
                    existing.has_local_charges = order_data.HasLocalCharges
                    existing.has_tex = order_data.HasTex
                    existing.notes = order_data.Notes
                    existing.additional_info = order_data.AdditionalInfo
                    existing.version = order_data.Version + 1
                    existing.last_sync = datetime.utcnow()
                    existing.device_id = request.DeviceId
                    
                    # Delete old containers and add new
                    db.query(CloudContainer).filter(CloudContainer.order_id == existing.id).delete()
                    for container_data in order_data.Containers:
                        container = CloudContainer(
                            order_id=existing.id,
                            local_id=container_data.Id,
                            container_number=container_data.ContainerNumber,
                            container_type=container_data.ContainerType,
                            weight=container_data.Weight,
                            volume=container_data.Volume,
                            loading_date=container_data.LoadingDate,
                            departure_date=container_data.DepartureDate,
                            arrival_iran_date=container_data.ArrivalIranDate,
                            truck_loading_date=container_data.TruckLoadingDate,
                            arrival_turkmenistan_date=container_data.ArrivalTurkmenistanDate,
                            client_receiving_date=container_data.ClientReceivingDate,
                            driver_first_name=container_data.DriverFirstName,
                            driver_last_name=container_data.DriverLastName,
                            driver_company=container_data.DriverCompany,
                            truck_number=container_data.TruckNumber,
                            driver_iran_phone=container_data.DriverIranPhone,
                            driver_turkmenistan_phone=container_data.DriverTurkmenistanPhone,
                            last_sync=datetime.utcnow()
                        )
                        db.add(container)
                    
                    # Delete old tasks and add new
                    db.query(CloudTask).filter(CloudTask.order_id == existing.id).delete()
                    for task_data in order_data.Tasks:
                        task = CloudTask(
                            order_id=existing.id,
                            local_id=task_data.TaskId,
                            description=task_data.Description,
                            assigned_to=task_data.AssignedTo,
                            status=task_data.Status,
                            priority=task_data.Priority,
                            due_date=task_data.DueDate,
                            created_date=task_data.CreatedDate or datetime.utcnow(),
                            last_sync=datetime.utcnow()
                        )
                        db.add(task)
                    
                    uploaded += 1
                    
                    # Notify about status change
                    if old_status != existing.status:
                        await notify_status_change(existing, old_status)
                    
                else:
                    # Create new order
                    new_order = CloudOrder(
                        local_id=order_data.Id or 0,
                        order_number=order_data.OrderNumber,
                        client_name=order_data.ClientName,
                        container_count=order_data.ContainerCount,
                        goods_type=order_data.GoodsType,
                        route=order_data.Route,
                        transit_port=order_data.TransitPort,
                        document_number=order_data.DocumentNumber,
                        chinese_transport_company=order_data.ChineseTransportCompany,
                        iranian_transport_company=order_data.IranianTransportCompany,
                        status=order_data.Status,
                        status_color=order_data.StatusColor,
                        creation_date=order_data.CreationDate or datetime.utcnow(),
                        departure_date=order_data.DepartureDate,
                        arrival_iran_date=order_data.ArrivalIranDate,
                        eta_date=order_data.EtaDate,
                        arrival_notice_date=order_data.ArrivalNoticeDate,
                        tkm_date=order_data.TkmDate,
                        loading_date=order_data.LoadingDate,
                        truck_loading_date=order_data.TruckLoadingDate,
                        arrival_turkmenistan_date=order_data.ArrivalTurkmenistanDate,
                        client_receiving_date=order_data.ClientReceivingDate,
                        has_loading_photo=order_data.HasLoadingPhoto,
                        has_local_charges=order_data.HasLocalCharges,
                        has_tex=order_data.HasTex,
                        notes=order_data.Notes,
                        additional_info=order_data.AdditionalInfo,
                        version=1,
                        last_sync=datetime.utcnow(),
                        device_id=request.DeviceId
                    )
                    db.add(new_order)
                    db.flush()
                    
                    # Add containers
                    for container_data in order_data.Containers:
                        container = CloudContainer(
                            order_id=new_order.id,
                            local_id=container_data.Id,
                            container_number=container_data.ContainerNumber,
                            container_type=container_data.ContainerType,
                            weight=container_data.Weight,
                            volume=container_data.Volume,
                            loading_date=container_data.LoadingDate,
                            departure_date=container_data.DepartureDate,
                            arrival_iran_date=container_data.ArrivalIranDate,
                            truck_loading_date=container_data.TruckLoadingDate,
                            arrival_turkmenistan_date=container_data.ArrivalTurkmenistanDate,
                            client_receiving_date=container_data.ClientReceivingDate,
                            driver_first_name=container_data.DriverFirstName,
                            driver_last_name=container_data.DriverLastName,
                            driver_company=container_data.DriverCompany,
                            truck_number=container_data.TruckNumber,
                            driver_iran_phone=container_data.DriverIranPhone,
                            driver_turkmenistan_phone=container_data.DriverTurkmenistanPhone,
                            last_sync=datetime.utcnow()
                        )
                        db.add(container)
                    
                    # Add tasks
                    for task_data in order_data.Tasks:
                        task = CloudTask(
                            order_id=new_order.id,
                            local_id=task_data.TaskId,
                            description=task_data.Description,
                            assigned_to=task_data.AssignedTo,
                            status=task_data.Status,
                            priority=task_data.Priority,
                            due_date=task_data.DueDate,
                            created_date=task_data.CreatedDate or datetime.utcnow(),
                            last_sync=datetime.utcnow()
                        )
                        db.add(task)
                    
                    uploaded += 1
                    
                    # Notify about new order
                    background_tasks.add_task(notify_new_order, new_order)
                
            except Exception as e:
                logger.error(f"Error processing order {order_data.OrderNumber}: {e}")
                conflicts.append({
                    "order_number": order_data.OrderNumber,
                    "type": "error",
                    "message": str(e)
                })
        
        # Commit all changes
        db.commit()
        
        # Log sync
        sync_log = SyncLog(
            device_id=request.DeviceId,
            sync_type="upload",
            records_synced=uploaded,
            status="success" if not conflicts else "partial",
            message=f"Uploaded {uploaded} orders, {len(conflicts)} conflicts"
        )
        db.add(sync_log)
        db.commit()
        
        logger.info(f"Sync completed: {uploaded} uploaded, {len(conflicts)} conflicts")
        
        return SyncResponse(
            Success=True,
            Message=f"Synchronized successfully. Uploaded: {uploaded}, Conflicts: {len(conflicts)}",
            OrdersUploaded=uploaded,
            OrdersDownloaded=downloaded,
            Conflicts=conflicts
        )
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
        db.rollback()
        
        # Log failed sync
        try:
            sync_log = SyncLog(
                device_id=request.DeviceId,
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
    finally:
        db.close()

@app.get("/sync/download")
async def download_data(device_id: str, last_sync: Optional[datetime] = None):
    """Download data from cloud - for WPF to get updates"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = SessionLocal()
    try:
        query = db.query(CloudOrder)
        
        if last_sync:
            query = query.filter(CloudOrder.last_sync > last_sync)
        
        orders = query.order_by(CloudOrder.last_sync.desc()).limit(100).all()
        
        result = []
        for order in orders:
            order_dict = {
                "Id": order.local_id,
                "OrderNumber": order.order_number,
                "ClientName": order.client_name,
                "ContainerCount": order.container_count,
                "GoodsType": order.goods_type,
                "Route": order.route,
                "TransitPort": order.transit_port,
                "DocumentNumber": order.document_number,
                "ChineseTransportCompany": order.chinese_transport_company,
                "IranianTransportCompany": order.iranian_transport_company,
                "Status": order.status,
                "StatusColor": order.status_color,
                "CreationDate": order.creation_date.isoformat() if order.creation_date else None,
                "DepartureDate": order.departure_date.isoformat() if order.departure_date else None,
                "ArrivalIranDate": order.arrival_iran_date.isoformat() if order.arrival_iran_date else None,
                "EtaDate": order.eta_date.isoformat() if order.eta_date else None,
                "ArrivalNoticeDate": order.arrival_notice_date.isoformat() if order.arrival_notice_date else None,
                "TkmDate": order.tkm_date.isoformat() if order.tkm_date else None,
                "LoadingDate": order.loading_date.isoformat() if order.loading_date else None,
                "TruckLoadingDate": order.truck_loading_date.isoformat() if order.truck_loading_date else None,
                "ArrivalTurkmenistanDate": order.arrival_turkmenistan_date.isoformat() if order.arrival_turkmenistan_date else None,
                "ClientReceivingDate": order.client_receiving_date.isoformat() if order.client_receiving_date else None,
                "HasLoadingPhoto": order.has_loading_photo,
                "HasLocalCharges": order.has_local_charges,
                "HasTex": order.has_tex,
                "Notes": order.notes,
                "AdditionalInfo": order.additional_info,
                "Version": order.version,
                "LastSync": order.last_sync.isoformat() if order.last_sync else None,
                "Containers": [],
                "Tasks": []
            }
            
            for container in order.containers:
                order_dict["Containers"].append({
                    "Id": container.local_id,
                    "ContainerNumber": container.container_number,
                    "ContainerType": container.container_type,
                    "Weight": float(container.weight) if container.weight else 0,
                    "Volume": float(container.volume) if container.volume else 0,
                    "LoadingDate": container.loading_date.isoformat() if container.loading_date else None,
                    "DepartureDate": container.departure_date.isoformat() if container.departure_date else None,
                    "ArrivalIranDate": container.arrival_iran_date.isoformat() if container.arrival_iran_date else None,
                    "TruckLoadingDate": container.truck_loading_date.isoformat() if container.truck_loading_date else None,
                    "ArrivalTurkmenistanDate": container.arrival_turkmenistan_date.isoformat() if container.arrival_turkmenistan_date else None,
                    "ClientReceivingDate": container.client_receiving_date.isoformat() if container.client_receiving_date else None,
                    "DriverFirstName": container.driver_first_name,
                    "DriverLastName": container.driver_last_name,
                    "DriverCompany": container.driver_company,
                    "TruckNumber": container.truck_number,
                    "DriverIranPhone": container.driver_iran_phone,
                    "DriverTurkmenistanPhone": container.driver_turkmenistan_phone
                })
            
            for task in order.tasks:
                order_dict["Tasks"].append({
                    "TaskId": task.local_id,
                    "OrderId": order.local_id,
                    "Description": task.description,
                    "AssignedTo": task.assigned_to,
                    "Status": task.status,
                    "Priority": task.priority,
                    "DueDate": task.due_date.isoformat() if task.due_date else None,
                    "CreatedDate": task.created_date.isoformat() if task.created_date else None
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
    finally:
        db.close()

@app.get("/drivers")
async def get_drivers(status: Optional[str] = None):
    """Get drivers information"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = SessionLocal()
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
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
