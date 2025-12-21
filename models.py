"""
Модели данных для бота записи на замер окон
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Client:
    """Модель клиента"""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Appointment:
    """Модель записи на встречу"""
    id: Optional[int]
    user_id: int
    date: str
    time: str
    address: str
    phone: str
    notes: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class KnowledgeBase:
    """Модель базы знаний"""
    id: Optional[int]
    question: str
    answer: str


