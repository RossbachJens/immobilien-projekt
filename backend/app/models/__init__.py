"""
Importiert alle ORM-Modelle, damit app.db.base.Base.metadata beim Import
dieses Pakets vollständig ist — Voraussetzung für Alembic --autogenerate.
"""

from app.models.buchhaltung import Account, EntryLine, JournalEntry  # noqa: F401
from app.models.dsgvo import AccessLog, GdprDeletionLog  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.stammdaten import Owner, Property, Tenant, Unit, User  # noqa: F401
from app.models.wirtschaftsplan import (  # noqa: F401
    BudgetPlan,
    BudgetPosition,
    ResolutionCollection,
    SpecialAssessment,
    UnitBudgetShare,
    UnitSpecialAssessmentShare,
)
from app.models.zuordnungen import (  # noqa: F401
    Lease,
    UnitAllocationKey,
    UnitOwnerHistory,
    UserProperty,
)
from app.models.abrechnung import (  # noqa: F401
    SettlementPeriod,
    SettlementPosition,
    SettlementPositionAccount,
    UnitSettlementShare,
    UnitSettlementSummary,
)
from app.models.bank_accounts import BankAccountPurpose, PropertyBankAccount  # noqa: F401

from app.models.meetings import MeetingAgendaItem, OwnerMeeting  # noqa: F401