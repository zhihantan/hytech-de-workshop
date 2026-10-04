"""Hytech DE 讲习班: 合成 MT5 交易湖仓数据和辅助工具。
Hytech DE workshop: synthetic MT5 trade-lakehouse data and helpers."""

from .config import DEFAULT_SERVERS, MT5_TABLES, SERVER_META, WorkshopConfig, participant_schema

__all__ = ["DEFAULT_SERVERS", "MT5_TABLES", "SERVER_META", "WorkshopConfig", "participant_schema"]
