"""
Equity Change Service

Business logic for creating, listing, and managing portfolio capital flows.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.equity_changes import EquityChange, EquityChangeType
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio, User

logger = get_logger(__name__)


class EquityChangeService:
    """Service layer for equity change CRUD operations and analytics."""

    EDIT_WINDOW_DAYS = 7
    DELETE_WINDOW_DAYS = 30

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_portfolio(self, portfolio_id: UUID, user_id: UUID) -> Portfolio:
        query = select(Portfolio).where(
            and_(Portfolio.id == portfolio_id, Portfolio.user_id == user_id, Portfolio.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            raise ValueError("EQUITY_004: Portfolio not found")
        return portfolio

    async def _get_equity_balance_for_date(self, portfolio_id: UUID, change_date: date) -> Decimal:
        # Try snapshot on or before change_date
        snapshot_query = (
            select(PortfolioSnapshot.equity_balance)
            .where(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.snapshot_date <= change_date,
            )
            .order_by(desc(PortfolioSnapshot.snapshot_date))
            .limit(1)
        )
        snapshot_result = await self.db.execute(snapshot_query)
        equity = snapshot_result.scalar_one_or_none()
        if equity is not None:
            return Decimal(equity)

        # Fallback to portfolio's current equity balance
        portfolio_query = select(Portfolio.equity_balance).where(Portfolio.id == portfolio_id)
        portfolio_result = await self.db.execute(portfolio_query)
        portfolio_equity = portfolio_result.scalar_one_or_none()
        if portfolio_equity is not None:
            return Decimal(portfolio_equity)

        return Decimal("0")

    def _validate_edit_window(self, equity_change: EquityChange) -> None:
        editable_until = equity_change.created_at + timedelta(days=self.EDIT_WINDOW_DAYS)
        if datetime.utcnow().replace(tzinfo=editable_until.tzinfo) > editable_until:
            raise ValueError("EQUITY_006: Equity changes can only be edited within 7 days of creation")

    def _validate_delete_window(self, equity_change: EquityChange) -> None:
        deletable_until = equity_change.created_at + timedelta(days=self.DELETE_WINDOW_DAYS)
        if datetime.utcnow().replace(tzinfo=deletable_until.tzinfo) > deletable_until:
            raise ValueError("EQUITY_007: Equity changes can only be deleted within 30 days of creation")

    async def list_equity_changes(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        page: int = 1,
        page_size: int = 25,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_deleted: bool = False,
    ) -> Tuple[List[EquityChange], int]:
        await self._get_portfolio(portfolio_id, user_id)

        filters = [EquityChange.portfolio_id == portfolio_id]
        if start_date:
            filters.append(EquityChange.change_date >= start_date)
        if end_date:
            filters.append(EquityChange.change_date <= end_date)
        if not include_deleted:
            filters.append(EquityChange.deleted_at.is_(None))

        base_query = select(EquityChange).where(and_(*filters))
        total_query = select(func.count()).select_from(EquityChange).where(and_(*filters))

        result_total = await self.db.execute(total_query)
        total_items = int(result_total.scalar() or 0)
        if total_items == 0:
            return [], 0

        offset = max(page - 1, 0) * page_size
        result = await self.db.execute(
            base_query.order_by(desc(EquityChange.change_date), desc(EquityChange.created_at))
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()
        return items, total_items

    async def create_equity_change(
        self,
        portfolio_id: UUID,
        user: User,
        change_type: EquityChangeType,
        amount: Decimal,
        change_date: date,
        notes: Optional[str] = None,
    ) -> EquityChange:
        portfolio = await self._get_portfolio(portfolio_id, user.id)

        if change_type == EquityChangeType.WITHDRAWAL:
            equity_balance = await self._get_equity_balance_for_date(portfolio_id, change_date)
            if amount > equity_balance:
                raise ValueError("EQUITY_003: Withdrawal amount cannot exceed current portfolio equity")

        equity_change = EquityChange(
            id=uuid4(),
            portfolio_id=portfolio_id,
            change_type=change_type,
            amount=amount,
            change_date=change_date,
            notes=notes,
            created_by_user_id=user.id,
        )

        self.db.add(equity_change)
        await self.db.commit()
        await self.db.refresh(equity_change)

        logger.info(
            "Created equity change %s for portfolio %s (type=%s amount=%.2f date=%s)",
            equity_change.id,
            portfolio_id,
            change_type,
            amount,
            change_date,
        )

        return equity_change

    async def get_equity_change(
        self,
        portfolio_id: UUID,
        equity_change_id: UUID,
        user_id: UUID,
        include_deleted: bool = False,
    ) -> EquityChange:
        await self._get_portfolio(portfolio_id, user_id)

        filters = [EquityChange.id == equity_change_id, EquityChange.portfolio_id == portfolio_id]
        if not include_deleted:
            filters.append(EquityChange.deleted_at.is_(None))

        query = select(EquityChange).where(and_(*filters))
        result = await self.db.execute(query)
        equity_change = result.scalar_one_or_none()
        if not equity_change:
            raise ValueError("EQUITY_008: Equity change not found")
        return equity_change

    async def update_equity_change(
        self,
        portfolio_id: UUID,
        equity_change_id: UUID,
        user_id: UUID,
        amount: Optional[Decimal] = None,
        change_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> EquityChange:
        equity_change = await self.get_equity_change(portfolio_id, equity_change_id, user_id)

        if equity_change.deleted_at is not None:
            raise ValueError("EQUITY_008: Equity change not found")

        self._validate_edit_window(equity_change)

        if amount is not None:
            if amount <= 0:
                raise ValueError("EQUITY_001: Amount must be greater than zero")
            if equity_change.change_type == EquityChangeType.WITHDRAWAL:
                effective_date = change_date or equity_change.change_date
                equity_balance = await self._get_equity_balance_for_date(portfolio_id, effective_date)
                if amount > equity_balance:
                    raise ValueError("EQUITY_003: Withdrawal amount cannot exceed current portfolio equity")
            equity_change.amount = amount

        if change_date is not None:
            if change_date > date.today():
                raise ValueError("EQUITY_002: Cannot record equity changes for future dates")
            if equity_change.change_type == EquityChangeType.WITHDRAWAL:
                equity_balance = await self._get_equity_balance_for_date(portfolio_id, change_date)
                if (equity_change.amount or Decimal("0")) > equity_balance:
                    raise ValueError("EQUITY_003: Withdrawal amount cannot exceed current portfolio equity")
            equity_change.change_date = change_date

        if notes is not None:
            equity_change.notes = notes

        equity_change.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(equity_change)

        logger.info("Updated equity change %s for portfolio %s", equity_change.id, portfolio_id)
        return equity_change

    async def delete_equity_change(
        self,
        portfolio_id: UUID,
        equity_change_id: UUID,
        user_id: UUID,
    ) -> None:
        equity_change = await self.get_equity_change(portfolio_id, equity_change_id, user_id)

        if equity_change.deleted_at is not None:
            raise ValueError("EQUITY_009: This equity change has already been deleted")

        self._validate_delete_window(equity_change)

        equity_change.deleted_at = datetime.utcnow()
        equity_change.updated_at = equity_change.deleted_at

        await self.db.commit()
        logger.info("Soft deleted equity change %s for portfolio %s", equity_change_id, portfolio_id)

    async def get_summary(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Decimal]:
        await self._get_portfolio(portfolio_id, user_id)

        filters = [EquityChange.portfolio_id == portfolio_id, EquityChange.deleted_at.is_(None)]
        if start_date:
            filters.append(EquityChange.change_date >= start_date)
        if end_date:
            filters.append(EquityChange.change_date <= end_date)

        contributions_case = case(
            (EquityChange.change_type == EquityChangeType.CONTRIBUTION, EquityChange.amount),
            else_=Decimal("0"),
        )
        withdrawals_case = case(
            (EquityChange.change_type == EquityChangeType.WITHDRAWAL, EquityChange.amount),
            else_=Decimal("0"),
        )

        summary_query = select(
            func.coalesce(func.sum(contributions_case), Decimal("0")),
            func.coalesce(func.sum(withdrawals_case), Decimal("0")),
        ).where(and_(*filters))

        result = await self.db.execute(summary_query)
        total_contributions, total_withdrawals = result.first() or (Decimal("0"), Decimal("0"))

        return {
            "total_contributions": Decimal(total_contributions or 0),
            "total_withdrawals": Decimal(total_withdrawals or 0),
        }

    async def get_period_summary(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        days: int,
    ) -> Dict[str, Decimal]:
        end = date.today()
        start = end - timedelta(days=days)
        return await self.get_summary(portfolio_id, user_id, start_date=start, end_date=end)

    async def get_last_change(
        self,
        portfolio_id: UUID,
        user_id: UUID,
    ) -> Optional[EquityChange]:
        await self._get_portfolio(portfolio_id, user_id)

        query = (
            select(EquityChange)
            .where(
                EquityChange.portfolio_id == portfolio_id,
                EquityChange.deleted_at.is_(None),
            )
            .order_by(desc(EquityChange.change_date), desc(EquityChange.created_at))
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def export_equity_changes(
        self,
        portfolio_id: UUID,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_deleted: bool = False,
    ) -> List[EquityChange]:
        await self._get_portfolio(portfolio_id, user_id)

        filters = [EquityChange.portfolio_id == portfolio_id]
        if start_date:
            filters.append(EquityChange.change_date >= start_date)
        if end_date:
            filters.append(EquityChange.change_date <= end_date)
        if not include_deleted:
            filters.append(EquityChange.deleted_at.is_(None))

        query = (
            select(EquityChange)
            .where(and_(*filters))
            .order_by(EquityChange.change_date.asc(), EquityChange.created_at.asc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()
