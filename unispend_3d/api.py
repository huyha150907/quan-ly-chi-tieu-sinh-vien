"""HTTP API for the UniSpend dashboard and its SQLite database."""

from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date as Date
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, Field

if __package__:
    from .backend import ExpenseBackend
    from .database import database_path
    from .models import EXPENSE_CATEGORIES
else:
    from backend import ExpenseBackend
    from database import database_path
    from models import EXPENSE_CATEGORIES


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.backend = ExpenseBackend(str(database_path()))
    yield


app = FastAPI(title="UniSpend API", description="Quản lý thu chi và ngân sách sinh viên", lifespan=lifespan)


def get_backend(request: Request) -> ExpenseBackend:
    return request.app.state.backend


Backend = Annotated[ExpenseBackend, Depends(get_backend)]
MONTH_PATTERN = r"^[0-9]{4}-(0[1-9]|1[0-2])$"
MonthPath = Annotated[str, Path(pattern=MONTH_PATTERN)]
MonthQuery = Annotated[str | None, Query(pattern=MONTH_PATTERN)]
TransactionType = Literal["Chi tiêu", "Thu nhập"]
Limit = Annotated[float, Field(ge=0, le=50_000_000, allow_inf_nan=False)]


class TransactionInput(BaseModel):
    date: Date
    tx_type: TransactionType
    category: str
    amount: float = Field(gt=0, le=500_000_000, allow_inf_nan=False)
    note: str = Field(default="", max_length=200)


class TransactionRecord(BaseModel):
    id: int
    date: str
    tx_type: str
    category: str
    amount: float
    note: str | None


class BudgetInput(BaseModel):
    total_budget: float = Field(ge=500_000, le=100_000_000, allow_inf_nan=False)
    category_limits: dict[str, Limit]


class BudgetRecord(BaseModel):
    month: str
    total_budget: float
    category_limits: dict[str, float]


@app.get("/health", tags=["Hệ thống"])
def health():
    return {"status": "ok"}


@app.get("/api/months", tags=["Báo cáo"])
def list_months(backend: Backend) -> list[str]:
    return backend.get_available_months()


@app.get("/api/categories", tags=["Giao dịch"])
def list_categories(tx_type: TransactionType, backend: Backend):
    return backend.get_categories(tx_type)


@app.get("/api/transactions", tags=["Giao dịch"])
def list_transactions(
    backend: Backend, month: MonthQuery = None, tx_type: TransactionType | None = None,
    category: str | None = None, q: Annotated[str | None, Query(max_length=200)] = None,
) -> list[TransactionRecord]:
    rows = backend.db.get_transactions_df(month)
    if tx_type:
        rows = rows[rows["tx_type"] == tx_type]
    if category:
        rows = rows[rows["category"] == category]
    if q and q.strip():
        rows = rows[rows["note"].astype("string").str.contains(q.strip(), case=False, regex=False, na=False)]
    return rows.drop(columns="month").to_dict(orient="records")


@app.post("/api/transactions", status_code=201, tags=["Giao dịch"])
def create_transaction(transaction: TransactionInput, backend: Backend) -> TransactionRecord:
    if transaction.category not in backend.get_categories(transaction.tx_type):
        raise HTTPException(422, "Danh mục không thuộc loại giao dịch đã chọn.")
    saved, message = backend.create_transaction(
        transaction.date.isoformat(), transaction.tx_type, transaction.category,
        transaction.amount, transaction.note,
    )
    if saved is None:
        raise HTTPException(422, message)
    return asdict(saved)


@app.delete("/api/transactions/{transaction_id}", status_code=204, tags=["Giao dịch"])
def delete_transaction(transaction_id: Annotated[int, Path(gt=0)], backend: Backend) -> Response:
    if not backend.remove_transaction(transaction_id):
        raise HTTPException(404, "Không tìm thấy giao dịch.")
    return Response(status_code=204)


@app.get("/api/dashboard/{month}", tags=["Báo cáo"])
def dashboard(month: MonthPath, backend: Backend):
    data = backend.get_monthly_dashboard_data(month)
    return {
        **{key: value for key, value in data.items() if not key.startswith("df_")},
        "category_summary": data["df_category_summary"].to_dict(orient="records"),
        "transaction_count": len(data["df_month"]),
    }


@app.get("/api/charts/{month}", tags=["Báo cáo"])
def charts(month: MonthPath, backend: Backend):
    return {name: frame.to_dict(orient="records") for name, frame in backend.get_charts_data(month).items()}


@app.get("/api/budgets/{month}", tags=["Ngân sách"])
def get_budget(month: MonthPath, backend: Backend) -> BudgetRecord:
    return asdict(backend.db.get_budget_config(month))


@app.put("/api/budgets/{month}", tags=["Ngân sách"])
def put_budget(month: MonthPath, budget: BudgetInput, backend: Backend) -> BudgetRecord:
    unknown_categories = budget.category_limits.keys() - EXPENSE_CATEGORIES.keys()
    if unknown_categories:
        raise HTTPException(422, f"Danh mục không hợp lệ ({', '.join(sorted(unknown_categories))}).")
    missing_categories = EXPENSE_CATEGORIES.keys() - budget.category_limits.keys()
    if missing_categories:
        raise HTTPException(422, f"Thiếu định mức ({', '.join(sorted(missing_categories))}).")
    limits = budget.category_limits
    backend.update_budget(month, budget.total_budget, limits)
    return BudgetRecord(month=month, total_budget=budget.total_budget, category_limits=limits)
