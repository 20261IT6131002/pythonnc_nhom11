from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import select
from hotel.models.entities import (AuditLog, Booking, Customer, HotelService, Invoice, Room, RoomType, User)
from hotel.repositories.catalog import HotelRepository
from hotel.services import business, catalog, chatbot, pdf_service
from hotel.services.security import verify_password
from hotel.controllers.utils import vnd


class ChatControllerMixin:
    def ask_chatbot(self, message):
        with self._session() as db:
            return chatbot.reply(db, message)
