"""Giao diện Tkinter cho ứng dụng quản lý chi tiêu sinh viên."""

import sqlite3
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from .charts import CategoryChart, MonthlyChart
from .storage import EXPENSE_CATEGORIES, INCOME_CATEGORIES, TYPE_LABELS
from .utils import display_date, money, parse_amount, shift_month, validate_month

BG = "#F3F6F3"
WHITE = "#FFFFFF"
INK = "#18342F"
MUTED = "#72817A"
GREEN = "#137C63"
RED = "#BC4D47"
LINE = "#E0E8E1"
TOTAL = "Tổng chi tiêu"


def label(parent, text, size=10, color=INK, bold=False, bg=None, **kwargs):
    return tk.Label(parent, text=text, font=("Segoe UI", size, "bold" if bold else "normal"),
                    fg=color, bg=bg or parent.cget("bg"), **kwargs)


def button(parent, text, command, primary=False, danger=False, **kwargs):
    return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                     bg=GREEN if primary else ("#FCECE9" if danger else "#E7EEE8"),
                     fg=WHITE if primary else (RED if danger else INK),
                     activebackground="#D4E7DB", activeforeground=INK,
                     font=("Segoe UI", 10, "bold"), padx=16, pady=9,
                     cursor="hand2", **kwargs)


class ExpenseApp(tk.Tk):
    def __init__(self, store, demo=False):
        super().__init__()
        self.store = store
        self.demo = demo
        self.month = date.today().strftime("%Y-%m")
        self.view = "Tổng quan"
        self.title("Ví sinh viên - Quản lý chi tiêu" + (" [DỮ LIỆU MẪU]" if demo else ""))
        width = min(1280, self.winfo_screenwidth() - 50)
        height = min(850, self.winfo_screenheight() - 80)
        self.geometry(f"{width}x{height}")
        self.minsize(1040, 720)
        self.configure(bg=BG)
        self.option_add("*Font", ("Segoe UI", 10))
        self._setup_style()
        self._build_shell()
        self.bind("<Control-n>", lambda _event: self.open_transaction())
        self.bind("<Control-N>", lambda _event: self.open_transaction())
        self.bind_all("<MouseWheel>", self._scroll_page, add="+")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.show_view(self.view)

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=INK,
                        rowheight=36, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#EDF3EE", foreground=MUTED,
                        font=("Segoe UI", 9, "bold"), padding=(8, 10), relief="flat")
        style.map("Treeview", background=[("selected", "#DCEFE5")],
                  foreground=[("selected", INK)])
        style.configure("TCombobox", padding=7, fieldbackground=WHITE)
        style.configure("TEntry", padding=7, fieldbackground=WHITE)

    def _build_shell(self):
        sidebar = tk.Frame(self, bg=INK, width=205)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        label(sidebar, "VÍ SINH VIÊN", 17, WHITE, True).pack(anchor="w", padx=23, pady=(32, 4))
        label(sidebar, "Chi tiêu nhỏ, kế hoạch lớn", 9, "#A8C7BA").pack(anchor="w", padx=23)
        label(sidebar, "KHÔNG GIAN CỦA BẠN", 8, "#8BA99D", True).pack(anchor="w", padx=23, pady=(42, 12))
        self.nav_buttons = {}
        for title in ("Tổng quan", "Giao dịch", "Ngân sách", "Thống kê"):
            b = tk.Button(sidebar, text=title, anchor="w", relief="flat", bd=0,
                          font=("Segoe UI", 11), fg="#BCD1C6", bg=INK,
                          activebackground="#294B40", activeforeground=WHITE,
                          padx=23, pady=15, cursor="hand2",
                          command=lambda t=title: self.show_view(t))
            b.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[title] = b
        bottom = tk.Frame(sidebar, bg=INK)
        bottom.pack(side="bottom", fill="x", padx=23, pady=25)
        label(bottom, "DỮ LIỆU MẪU" if self.demo else "DỮ LIỆU CÁ NHÂN",
              9, "#B8D9A0", True).pack(anchor="w")
        label(bottom, "Lưu trên máy của bạn\nPython + SQLite", 9, "#95B0A2",
              justify="left").pack(anchor="w", pady=(8, 0))

        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True, padx=26, pady=23)
        head = tk.Frame(main, bg=BG)
        head.pack(fill="x")
        title_block = tk.Frame(head, bg=BG)
        title_block.pack(side="left")
        self.heading = label(title_block, "", 24, bold=True)
        self.heading.pack(anchor="w")
        self.subtitle = label(title_block, "", 10, MUTED)
        self.subtitle.pack(anchor="w", pady=(3, 0))
        button(head, "+ Thêm giao dịch", self.open_transaction, primary=True).pack(side="right", pady=5)

        month_row = tk.Frame(main, bg=BG)
        month_row.pack(fill="x", pady=(20, 16))
        tk.Button(month_row, text="‹", command=lambda: self.change_month(-1),
                  bg=WHITE, fg=INK, relief="flat", font=("Segoe UI", 15), width=3).pack(side="left")
        self.month_var = tk.StringVar(value=self.month)
        month_entry = ttk.Entry(month_row, textvariable=self.month_var, width=10, justify="center")
        month_entry.pack(side="left", padx=6)
        month_entry.bind("<Return>", lambda _event: self.apply_month())
        tk.Button(month_row, text="›", command=lambda: self.change_month(1),
                  bg=WHITE, fg=INK, relief="flat", font=("Segoe UI", 15), width=3).pack(side="left")
        button(month_row, "Xem tháng", self.apply_month).pack(side="left", padx=8)
        button(month_row, "Tháng này", self.current_month).pack(side="left")
        label(month_row, "Đơn vị: đồng (VND)", 9, MUTED).pack(side="right")
        self.status_var = tk.StringVar(value="Sẵn sàng. Ctrl+N để thêm giao dịch.")
        tk.Label(main, textvariable=self.status_var, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(side="bottom", fill="x", pady=(12, 0))
        self.content_host = tk.Frame(main, bg=BG)
        self.content_host.pack(fill="both", expand=True)
        self.content = self.content_host

    def show_view(self, view):
        self.view = view
        for widget in self.content_host.winfo_children():
            widget.destroy()
        self.content = self.content_host
        self.page_canvas = None
        # Các trang báo cáo có thể cuộn trên màn hình nhỏ; bảng giao dịch tự cuộn.
        if view in ("Tổng quan", "Thống kê"):
            self.page_canvas = tk.Canvas(self.content_host, bg=BG, highlightthickness=0)
            scrollbar = ttk.Scrollbar(self.content_host, orient="vertical", command=self.page_canvas.yview)
            scrollbar.pack(side="right", fill="y")
            self.page_canvas.configure(yscrollcommand=scrollbar.set)
            self.page_canvas.pack(side="left", fill="both", expand=True)
            self.content = tk.Frame(self.page_canvas, bg=BG)
            item = self.page_canvas.create_window(0, 0, window=self.content, anchor="nw")
            self.content.bind("<Configure>", lambda _e: self.page_canvas.configure(
                scrollregion=self.page_canvas.bbox("all")))
            self.page_canvas.bind("<Configure>", lambda e: self.page_canvas.itemconfigure(item, width=e.width))
        for name, b in self.nav_buttons.items():
            b.configure(bg="#31584A" if name == view else INK,
                        fg=WHITE if name == view else "#BCD1C6")
        subtitles = {
            "Tổng quan": "Nắm rõ từng khoản thu chi, chủ động hơn mỗi ngày.",
            "Giao dịch": "Ghi lại và tìm kiếm các khoản thu chi của bạn.",
            "Ngân sách": "Đặt giới hạn cho tháng và từng nhóm chi tiêu.",
            "Thống kê": "Hiểu tiền của bạn đang đi đâu qua từng tháng.",
        }
        self.heading.configure(text=view)
        self.subtitle.configure(text=subtitles[view])
        {"Tổng quan": self._dashboard, "Giao dịch": self._transactions,
         "Ngân sách": self._budgets, "Thống kê": self._statistics}[view]()

    def _scroll_page(self, event):
        if self.page_canvas is not None and self.grab_current() is None:
            if self.page_canvas.bbox("all")[3] > self.page_canvas.winfo_height():
                self.page_canvas.yview_scroll(-int(event.delta / 120), "units")

    def apply_month(self):
        try:
            self.month = validate_month(self.month_var.get().strip())
        except ValueError as exc:
            messagebox.showerror("Tháng không hợp lệ", str(exc), parent=self)
            self.month_var.set(self.month)
            return
        self.month_var.set(self.month)
        self.show_view(self.view)

    def change_month(self, offset):
        try:
            self.month = shift_month(self.month, offset)
        except ValueError as exc:
            messagebox.showerror("Không thể chuyển tháng", str(exc), parent=self)
            return
        self.month_var.set(self.month)
        self.show_view(self.view)

    def current_month(self):
        self.month_var.set(date.today().strftime("%Y-%m"))
        self.apply_month()

    def _panel(self, parent, title, subtitle=None):
        frame = tk.Frame(parent, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
        label(frame, title, 12, bold=True).pack(anchor="w", padx=18, pady=(15, 0))
        if subtitle:
            label(frame, subtitle, 9, MUTED).pack(anchor="w", padx=18, pady=(3, 0))
        return frame

    def _metrics(self, parent):
        summary = self.store.summary(self.month)
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 16))
        data = (("TỔNG THU NHẬP", summary["income"], GREEN, "Trong tháng đang chọn"),
                ("TỔNG CHI TIÊU", summary["expense"], RED, f"{summary['count']} giao dịch thu và chi"),
                ("CHÊNH LỆCH THU CHI", summary["balance"], INK, "Thu nhập trừ chi tiêu trong tháng"))
        for i, (title, value, color, hint) in enumerate(data):
            row.columnconfigure(i, weight=1, uniform="cards")
            card = tk.Frame(row, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
            label(card, title, 9, MUTED, True).pack(anchor="w", padx=17, pady=(14, 4))
            label(card, money(value), 22, color, True).pack(anchor="w", padx=17)
            label(card, hint, 9, MUTED).pack(anchor="w", padx=17, pady=(3, 14))

    def _budget_banner(self, parent):
        statuses = self.store.budget_statuses(self.month)
        exceeded = [s for s in statuses if s.exceeded]
        near = [s for s in statuses if s.near_limit and not s.exceeded]
        if exceeded:
            text = "Vượt ngân sách: " + "; ".join(f"{s.category} +{money(-s.remaining)}" for s in exceeded)
            bg, color = "#FCEDEA", RED
        elif near:
            text = "Sắp hết ngân sách: " + "; ".join(f"{s.category} ({s.ratio:.0%})" for s in near)
            bg, color = "#FFF3DB", "#93631C"
        elif statuses:
            text = "Bạn đang chi tiêu trong ngân sách. Tiếp tục giữ thói quen ghi chép nhé."
            bg, color = "#E4F1E8", GREEN
        else:
            text = "Chưa đặt ngân sách tháng này. Vào mục Ngân sách để bật cảnh báo."
            bg, color = "#E8EFEA", MUTED
        label(parent, text, 10, color, bg=bg, anchor="w", wraplength=850,
              justify="left", padx=14, pady=11).pack(fill="x", pady=(0, 16))

    def _chart_pair(self, parent, height=210):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="both", expand=True, pady=(0, 16))
        row.columnconfigure(0, weight=1, uniform="charts")
        row.columnconfigure(1, weight=1, uniform="charts")
        row.rowconfigure(0, weight=1)
        categories = self._panel(row, "Chi tiêu theo danh mục", f"Tháng {self.month[5:]}/{self.month[:4]}")
        categories.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        CategoryChart(categories, self.store.category_totals(self.month), height=height).pack(
            fill="both", expand=True, padx=18, pady=14)
        months = self._panel(row, "Thu chi qua các tháng", "6 tháng gần nhất đến tháng đang chọn")
        months.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        year, month = map(int, self.month.split("-"))
        count = min(6, (year - 1) * 12 + month)
        MonthlyChart(months, self.store.monthly_totals(self.month, count=count), height=height).pack(
            fill="both", expand=True, padx=14, pady=14)

    def _dashboard(self):
        self._metrics(self.content)
        self._budget_banner(self.content)
        self._chart_pair(self.content, 185)
        panel = self._panel(self.content, "Giao dịch gần đây", "Trong tháng đang chọn")
        panel.pack(fill="both", expand=True)
        records = self.store.list_transactions(month=self.month)[:5]
        self._make_table(panel, records, height=4, editable=False)
        if not records:
            label(panel, "Chưa có giao dịch. Chọn + Thêm giao dịch để bắt đầu.", 10, MUTED).pack(pady=(0, 14))

    def _make_table(self, parent, records, height=8, editable=True):
        wrapper = tk.Frame(parent, bg=WHITE)
        wrapper.pack(fill="both", expand=True, padx=14, pady=12)
        columns = ("date", "kind", "category", "note", "amount")
        table = ttk.Treeview(wrapper, columns=columns, show="headings", height=height,
                             selectmode="browse")
        for column, title, width, anchor in (
            ("date", "NGÀY", 95, "w"), ("kind", "LOẠI", 95, "w"),
            ("category", "DANH MỤC", 135, "w"), ("note", "GHI CHÚ", 215, "w"),
            ("amount", "SỐ TIỀN", 135, "e")):
            table.heading(column, text=title, anchor=anchor)
            table.column(column, width=width, minwidth=65, anchor=anchor,
                         stretch=column in ("note", "category"))
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        table.tag_configure("income", foreground=GREEN)
        table.tag_configure("expense", foreground=INK)
        for record in records:
            sign = "+" if record.kind == "income" else "−"
            table.insert("", "end", iid=str(record.id), tags=(record.kind,), values=(
                display_date(record.date), TYPE_LABELS[record.kind], record.category,
                record.note or "—", f"{sign}{money(record.amount)}"))
        if editable:
            table.bind("<Double-1>", lambda _event: self.edit_selected())
        return table

    def _transactions(self):
        filters = tk.Frame(self.content, bg=BG)
        filters.pack(fill="x", pady=(0, 12))
        self.kind_var = tk.StringVar(value=getattr(self, "filter_kind", "Tất cả loại"))
        self.category_var = tk.StringVar(value=getattr(self, "filter_category", "Tất cả danh mục"))
        self.search_var = tk.StringVar(value=getattr(self, "filter_search", ""))
        for var, values, width in ((self.kind_var, ("Tất cả loại", "Chi tiêu", "Thu nhập"), 13),
                                   (self.category_var, ("Tất cả danh mục", *dict.fromkeys(
                                       (*EXPENSE_CATEGORIES, *INCOME_CATEGORIES))), 19)):
            combo = ttk.Combobox(filters, textvariable=var, values=values, state="readonly", width=width)
            combo.pack(side="left", padx=(0, 8))
            combo.bind("<<ComboboxSelected>>", lambda _event: self.apply_filters())
        entry = ttk.Entry(filters, textvariable=self.search_var, width=22)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        entry.bind("<Return>", lambda _event: self.apply_filters())
        button(filters, "Tìm", self.apply_filters).pack(side="left", padx=(0, 8))
        button(filters, "Bỏ lọc", self.reset_filters).pack(side="left")

        kind = {"Chi tiêu": "expense", "Thu nhập": "income"}.get(self.kind_var.get())
        category = None if self.category_var.get() == "Tất cả danh mục" else self.category_var.get()
        self.filtered_records = self.store.list_transactions(month=self.month, kind=kind,
                                                             category=category, search=self.search_var.get())
        income = sum(r.amount for r in self.filtered_records if r.kind == "income")
        expense = sum(r.amount for r in self.filtered_records if r.kind == "expense")
        label(self.content, f"{len(self.filtered_records)} giao dịch  •  Thu {money(income)}  •  Chi {money(expense)}",
              10, MUTED).pack(anchor="w", pady=(0, 12))
        panel = self._panel(self.content, "Sổ thu chi", "Tìm theo ghi chú hoặc danh mục. Nhấp đúp vào một dòng để sửa.")
        panel.pack(fill="both", expand=True)
        self.transaction_table = self._make_table(panel, self.filtered_records)
        if not self.filtered_records:
            label(panel, "Không có giao dịch phù hợp.", 10, MUTED).pack(pady=(0, 16))
        tools = tk.Frame(self.content, bg=BG)
        tools.pack(side="bottom", before=panel, fill="x", pady=(14, 0))
        button(tools, "Sửa giao dịch", self.edit_selected).pack(side="left", padx=(0, 8))
        button(tools, "Xóa giao dịch", self.delete_selected, danger=True).pack(side="left")
        button(tools, "Xuất CSV", self.export_transactions).pack(side="right")

    def apply_filters(self):
        self.filter_kind = self.kind_var.get()
        self.filter_category = self.category_var.get()
        self.filter_search = self.search_var.get().strip()
        self.show_view("Giao dịch")

    def reset_filters(self):
        self.filter_kind, self.filter_category, self.filter_search = "Tất cả loại", "Tất cả danh mục", ""
        self.show_view("Giao dịch")

    def selected_transaction(self):
        selection = self.transaction_table.selection()
        if not selection:
            messagebox.showinfo("Chọn giao dịch", "Hãy chọn một dòng giao dịch trước.", parent=self)
            return None
        return next((r for r in self.filtered_records if r.id == int(selection[0])), None)

    def edit_selected(self):
        record = self.selected_transaction()
        if record:
            self.open_transaction(record)

    def delete_selected(self):
        record = self.selected_transaction()
        if not record:
            return
        if messagebox.askyesno("Xóa giao dịch", f"Xóa khoản {TYPE_LABELS[record.kind].lower()} "
                               f"{money(record.amount)} ngày {display_date(record.date)}?", parent=self):
            try:
                self.store.delete_transaction(record.id)
            except (ValueError, sqlite3.Error) as exc:
                messagebox.showerror("Không thể xóa", str(exc), parent=self)
                return
            self.show_view(self.view)
            self.status_var.set("Đã xóa giao dịch.")

    def export_transactions(self):
        path = filedialog.asksaveasfilename(parent=self, title="Xuất các giao dịch đang lọc",
                                          defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                          initialfile=f"thu_chi_{self.month}.csv")
        if path:
            try:
                count = self.store.export_csv(path, self.filtered_records)
            except (OSError, sqlite3.Error) as exc:
                messagebox.showerror("Không xuất được CSV", str(exc), parent=self)
                return
            self.status_var.set(f"Đã xuất {count} giao dịch: {path}")

    def _budgets(self):
        self._budget_banner(self.content)
        tools = tk.Frame(self.content, bg=BG)
        tools.pack(fill="x", pady=(0, 14))
        label(tools, "Cảnh báo từ 80% • Vượt ngân sách khi chi > giới hạn", 10, MUTED).pack(side="left")
        button(tools, "+ Đặt ngân sách", self.open_budget, primary=True).pack(side="right")
        statuses = self.store.budget_statuses(self.month)
        panel = self._panel(self.content, "Ngân sách tháng", "Chọn một dòng để thay đổi hoặc gỡ giới hạn.")
        panel.pack(fill="both", expand=True)
        wrapper = tk.Frame(panel, bg=WHITE)
        wrapper.pack(fill="both", expand=True, padx=16, pady=15)
        cols = ("category", "limit", "spent", "remaining", "state")
        self.budget_table = ttk.Treeview(wrapper, columns=cols, show="headings", selectmode="browse")
        for name, title, width in (("category", "DANH MỤC", 150), ("limit", "GIỚI HẠN", 135),
                                   ("spent", "ĐÃ CHI", 135), ("remaining", "CÒN LẠI", 135),
                                   ("state", "TRẠNG THÁI", 150)):
            self.budget_table.heading(name, text=title, anchor="w")
            self.budget_table.column(name, width=width, minwidth=90, anchor="w")
        self.budget_table.pack(fill="both", expand=True)
        self.budget_table.tag_configure("over", foreground=RED)
        self.budget_table.tag_configure("near", foreground="#9A6C21")
        for s in statuses:
            text = "Vượt" if s.exceeded else ("Sắp hết" if s.near_limit else "Trong ngân sách")
            self.budget_table.insert("", "end", iid=s.category, values=(s.category, money(s.limit),
                                     money(s.spent), money(s.remaining), f"{text} ({s.ratio:.0%})"),
                                     tags=("over" if s.exceeded else "near" if s.near_limit else "ok",))
        self.budget_table.bind("<Double-1>", lambda _event: self.edit_budget())
        if not statuses:
            label(panel, "Đặt ngân sách tổng hoặc từng danh mục để bắt đầu.", 10, MUTED).pack(pady=(0, 20))
        actions = tk.Frame(self.content, bg=BG)
        actions.pack(side="bottom", before=panel, fill="x", pady=(14, 0))
        button(actions, "Sửa ngân sách", self.edit_budget).pack(side="left", padx=(0, 8))
        button(actions, "Gỡ ngân sách", self.remove_budget, danger=True).pack(side="left")
        label(actions, "Ngân sách tổng và danh mục được kiểm tra riêng.", 9, MUTED).pack(side="right")

    def edit_budget(self):
        selected = self.budget_table.selection()
        if not selected:
            messagebox.showinfo("Chọn ngân sách", "Hãy chọn một ngân sách trước.", parent=self)
            return
        status = next(s for s in self.store.budget_statuses(self.month) if s.category == selected[0])
        self.open_budget(status)

    def remove_budget(self):
        selected = self.budget_table.selection()
        if not selected:
            messagebox.showinfo("Chọn ngân sách", "Hãy chọn một ngân sách trước.", parent=self)
            return
        if messagebox.askyesno("Gỡ ngân sách", f"Gỡ giới hạn {selected[0]} của tháng {self.month}?", parent=self):
            try:
                self.store.remove_budget(self.month, selected[0])
            except (ValueError, sqlite3.Error) as exc:
                messagebox.showerror("Không thể gỡ", str(exc), parent=self)
                return
            self.show_view("Ngân sách")
            self.status_var.set("Đã gỡ ngân sách. Các giao dịch vẫn được giữ nguyên.")

    def _statistics(self):
        self._metrics(self.content)
        self._chart_pair(self.content, 230)
        totals = self.store.category_totals(self.month)
        total = sum(totals.values())
        panel = self._panel(self.content, "Tỷ trọng chi tiêu", "Chi tiết từng danh mục trong tháng đang chọn")
        panel.pack(fill="x")
        row = tk.Frame(panel, bg=WHITE)
        row.pack(fill="x", padx=18, pady=16)
        for i, (category, amount) in enumerate(totals.items()):
            row.columnconfigure(i, weight=1, uniform="stats")
            block = tk.Frame(row, bg=WHITE)
            block.grid(row=0, column=i, sticky="nsew", padx=4)
            label(block, category, 10, MUTED).pack(anchor="w")
            label(block, f"{amount / total:.1%}" if total else "0%", 19, GREEN, True).pack(anchor="w", pady=4)
            label(block, money(amount), 9).pack(anchor="w")

    def _dialog(self, title, width=470, height=545):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.configure(bg=WHITE)
        dialog.resizable(False, False)
        x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.transient(self)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        body = tk.Frame(dialog, bg=WHITE)
        body.pack(fill="both", expand=True, padx=27, pady=23)
        label(body, title, 20, bold=True).pack(anchor="w", pady=(0, 15))
        return dialog, body

    @staticmethod
    def _form_field(parent, title, variable, values=None, readonly=False):
        label(parent, title, 10, MUTED).pack(anchor="w", pady=(9, 5))
        if values is not None:
            widget = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        else:
            widget = ttk.Entry(parent, textvariable=variable, state="readonly" if readonly else "normal")
        widget.pack(fill="x")
        return widget

    def open_transaction(self, record=None):
        # Không mở thêm hộp nhập khi người dùng đang sửa một hộp khác.
        if self.grab_current() is not None:
            return
        dialog, body = self._dialog("Sửa giao dịch" if record else "Thêm giao dịch")
        default_date = date.today().isoformat() if self.month == date.today().strftime("%Y-%m") else self.month + "-01"
        kind_var = tk.StringVar(value=TYPE_LABELS[record.kind] if record else "Chi tiêu")
        date_var = tk.StringVar(value=record.date if record else default_date)
        category_var = tk.StringVar(value=record.category if record else EXPENSE_CATEGORIES[0])
        amount_var = tk.StringVar(value=str(record.amount) if record else "")
        note_var = tk.StringVar(value=record.note if record else "")
        kind_box = self._form_field(body, "Loại giao dịch", kind_var, list(TYPE_LABELS.values()))
        self._form_field(body, "Ngày (YYYY-MM-DD)", date_var)
        category_box = self._form_field(body, "Danh mục", category_var, EXPENSE_CATEGORIES)

        def update_categories(_event=None):
            categories = INCOME_CATEGORIES if kind_var.get() == "Thu nhập" else EXPENSE_CATEGORIES
            category_box.configure(values=categories)
            if category_var.get() not in categories:
                category_var.set(categories[0])

        kind_box.bind("<<ComboboxSelected>>", update_categories)
        update_categories()
        amount_entry = self._form_field(body, "Số tiền (VND), ví dụ 50.000", amount_var)
        self._form_field(body, "Ghi chú (tối đa 200 ký tự)", note_var)
        error_var = tk.StringVar()
        tk.Label(body, textvariable=error_var, bg=WHITE, fg=RED, font=("Segoe UI", 9),
                 wraplength=410, anchor="w", justify="left").pack(fill="x", pady=(10, 0))

        def save():
            try:
                kind = "income" if kind_var.get() == "Thu nhập" else "expense"
                values = (date_var.get().strip(), kind, category_var.get(),
                          parse_amount(amount_var.get()), note_var.get())
                if record:
                    self.store.update_transaction(record.id, *values)
                else:
                    self.store.add_transaction(*values)
            except (ValueError, sqlite3.Error) as exc:
                error_var.set(str(exc))
                return
            saved_month = values[0][:7]
            self.month = saved_month
            self.month_var.set(saved_month)
            dialog.destroy()
            self.show_view(self.view)
            self.status_var.set("Đã lưu giao dịch.")
            if kind == "expense":
                alerts = [s for s in self.store.budget_statuses(saved_month)
                          if s.category in (TOTAL, values[2]) and (s.exceeded or s.near_limit)]
                if alerts:
                    lines = []
                    for status in alerts:
                        if status.exceeded:
                            lines.append(f"{status.category}: vượt {money(-status.remaining)} "
                                         f"(đã chi {money(status.spent)} / {money(status.limit)}).")
                        else:
                            lines.append(f"{status.category}: đã dùng {status.ratio:.0%}, "
                                         f"còn {money(status.remaining)}.")
                    messagebox.showwarning("Lưu ý ngân sách", "\n".join(lines), parent=self)

        actions = tk.Frame(body, bg=WHITE)
        actions.pack(side="bottom", fill="x", pady=(12, 0))
        button(actions, "Lưu giao dịch", save, primary=True).pack(side="right")
        button(actions, "Hủy", dialog.destroy).pack(side="right", padx=8)
        dialog.bind("<Return>", lambda _event: save())
        amount_entry.focus_set()

    def open_budget(self, status=None):
        dialog, body = self._dialog("Sửa ngân sách" if status else "Đặt ngân sách", height=365)
        label(body, f"Áp dụng cho tháng {self.month[5:]}/{self.month[:4]}", 10, MUTED).pack(anchor="w")
        category_var = tk.StringVar(value=status.category if status else TOTAL)
        amount_var = tk.StringVar(value=str(status.limit) if status else "")
        category_box = self._form_field(body, "Ngân sách cho", category_var, (TOTAL, *EXPENSE_CATEGORIES))
        if status:
            category_box.configure(state="disabled")
        amount_entry = self._form_field(body, "Giới hạn chi tiêu (VND)", amount_var)
        error_var = tk.StringVar()
        tk.Label(body, textvariable=error_var, bg=WHITE, fg=RED, font=("Segoe UI", 9),
                 wraplength=410, anchor="w", justify="left").pack(fill="x", pady=(8, 0))

        def save():
            try:
                amount = parse_amount(amount_var.get())
                existing = next((s for s in self.store.budget_statuses(self.month)
                                 if s.category == category_var.get()), None)
                if not status and existing and not messagebox.askyesno(
                        "Thay ngân sách", f"{category_var.get()} đã có giới hạn {money(existing.limit)}. "
                        f"Thay bằng {money(amount)}?", parent=dialog):
                    return
                self.store.set_budget(self.month, category_var.get(), amount)
            except (ValueError, sqlite3.Error) as exc:
                error_var.set(str(exc))
                return
            dialog.destroy()
            self.show_view("Ngân sách")
            self.status_var.set("Đã lưu ngân sách tháng.")

        actions = tk.Frame(body, bg=WHITE)
        actions.pack(side="bottom", fill="x", pady=(10, 0))
        button(actions, "Lưu ngân sách", save, primary=True).pack(side="right")
        button(actions, "Hủy", dialog.destroy).pack(side="right", padx=8)
        dialog.bind("<Return>", lambda _event: save())
        amount_entry.focus_set()
