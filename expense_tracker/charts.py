"""Biểu đồ Canvas: không cần matplotlib hay kết nối Internet."""

import tkinter as tk

from .utils import compact_money, money

INK = "#18342F"
MUTED = "#74827E"
GRID = "#E8EFEB"
GREEN = "#159475"
ORANGE = "#E6A15A"
COLORS = (GREEN, "#70B5A3", "#D8AC62", "#8B9EC2", "#C78EA2", "#B1BFB5")


class CategoryChart(tk.Canvas):
    def __init__(self, master, totals, **kwargs):
        super().__init__(master, bg="white", highlightthickness=0, **kwargs)
        self.totals = totals
        self.bind("<Configure>", lambda _event: self.draw())

    def draw(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 40 or height < 40:
            return
        total = sum(self.totals.values())
        if not total:
            self.create_text(width / 2, height / 2, text="Chưa có chi tiêu trong tháng này",
                             fill=MUTED, font=("Segoe UI", 11))
            return
        maximum = max(self.totals.values())
        row_height = min(34, (height - 8) / max(len(self.totals), 1))
        left, right = 87, max(100, width - 112)
        for index, (category, amount) in enumerate(self.totals.items()):
            y = 10 + index * row_height
            self.create_text(0, y + 5, text=category, anchor="w", fill=INK,
                             font=("Segoe UI", 10))
            self.create_rectangle(left, y, right, y + 11, fill=GRID, outline="")
            if amount:
                self.create_rectangle(left, y, left + (right - left) * amount / maximum,
                                      y + 11, fill=COLORS[index % len(COLORS)], outline="")
            self.create_text(width - 2, y + 5, text=money(amount), anchor="e",
                             fill=MUTED, font=("Segoe UI", 9))


class MonthlyChart(tk.Canvas):
    def __init__(self, master, months, **kwargs):
        super().__init__(master, bg="white", highlightthickness=0, **kwargs)
        self.months = months
        self.bind("<Configure>", lambda _event: self.draw())

    def draw(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 40 or height < 60:
            return
        self.create_rectangle(width - 175, 3, width - 165, 13, fill=GREEN, outline="")
        self.create_text(width - 160, 8, text="Thu nhập", anchor="w", fill=MUTED,
                         font=("Segoe UI", 9))
        self.create_rectangle(width - 82, 3, width - 72, 13, fill=ORANGE, outline="")
        self.create_text(width - 67, 8, text="Chi tiêu", anchor="w", fill=MUTED,
                         font=("Segoe UI", 9))
        maximum = max((max(m["income"], m["expense"]) for m in self.months), default=0)
        if not maximum:
            self.create_text(width / 2, height / 2, text="Thêm giao dịch để xem biểu đồ",
                             fill=MUTED, font=("Segoe UI", 11))
            return
        # Làm tròn cận trên để cột cao nhất vẫn có khoảng trống.
        maximum = maximum * 1.15
        left, top, bottom = 48, 30, height - 28
        plot_height = max(1, bottom - top)
        for tick in range(4):
            y = bottom - plot_height * tick / 3
            self.create_line(left, y, width - 8, y, fill=GRID)
            self.create_text(left - 7, y, text=compact_money(maximum * tick / 3),
                             anchor="e", fill=MUTED, font=("Segoe UI", 8))
        step = (width - left - 8) / len(self.months)
        bar = min(19, step * .28)
        for index, row in enumerate(self.months):
            center = left + step * (index + .5)
            for key, color, x in (("income", GREEN, center - bar - 2),
                                   ("expense", ORANGE, center + 2)):
                value = row[key]
                if value:
                    self.create_rectangle(x, bottom - plot_height * value / maximum,
                                          x + bar, bottom, fill=color, outline="")
            label = row["month"][5:] + "/" + row["month"][2:4]
            self.create_text(center, bottom + 16, text=label, fill=MUTED,
                             font=("Segoe UI", 9))
