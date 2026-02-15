from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QToolTip
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PySide6.QtGui import QPainter, QColor, QCursor
from PySide6.QtCore import Qt
from src.core.analytics import analytics

class StatsTab(QWidget):
    def __init__(self):
        super().__init__()
        
        # Основний лейаут: горизонтальний для двох графіків
        self.layout = QHBoxLayout(self)
        
        # --- 1. Pie Chart (Категорії) ---
        self.pie_chart_view = self.create_pie_chart()
        self.layout.addWidget(self.pie_chart_view)
        
        # --- 2. Bar Chart (Прогноз) ---
        self.bar_chart_view = self.create_bar_chart()
        self.layout.addWidget(self.bar_chart_view)
        
        # Завантаження даних
        self.refresh_stats()

    def create_pie_chart(self):
        self.pie_series = QPieSeries()
        self.pie_series.hovered.connect(self.on_pie_slice_hovered)
        
        chart = QChart()
        chart.addSeries(self.pie_series)
        chart.setTitle("Розподіл витрат за категоріями")
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return view

    def create_bar_chart(self):
        self.bar_set = QBarSet("Прогноз витрат (UAH)")
        self.bar_set.setColor(QColor("#3f51b5")) # Material Design Blue
        self.bar_set.hovered.connect(self.on_bar_hovered)
        
        self.bar_series = QBarSeries()
        self.bar_series.append(self.bar_set)
        
        chart = QChart()
        chart.addSeries(self.bar_series)
        chart.setTitle("Прогноз на 12 місяців")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        # Осі
        self.axis_x = QBarCategoryAxis()
        chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.bar_series.attachAxis(self.axis_x)
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Сума (UAH)")
        chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.bar_series.attachAxis(self.axis_y)
        
        chart.legend().setVisible(False)
        
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return view

    def refresh_stats(self):
        """Оновлює дані графіків."""
        self._update_pie_chart()
        self._update_bar_chart()

    def _update_pie_chart(self):
        self.pie_series.clear()
        data = analytics.get_expenses_by_category()
        
        for category, amount in data.items():
            slice_ = self.pie_series.append(category, amount)
            slice_.setLabel(f"{category}: {amount:.0f} ₴")
            # Показувати лейбли, якщо частка > 5%
            if amount > 0: # Спрощено, можна додати логіку %
                slice_.setLabelVisible(True)

    def _update_bar_chart(self):
        # Очищення старого набору (через створення нового, QtCharts специфіка)
        # QBarSet не має методу clear(), тому ми просто оновлюємо значення або перестворюємо
        self.bar_set.remove(0, self.bar_set.count())
        self.axis_x.clear()
        
        forecast_data = analytics.get_monthly_forecast(12)
        
        categories = []
        max_val = 0
        
        for date_obj, amount in forecast_data:
            self.bar_set.append(amount)
            categories.append(date_obj.strftime("%b %Y")) # Jan 2026
            if amount > max_val:
                max_val = amount
                
        self.axis_x.append(categories)
        self.axis_y.setRange(0, max_val * 1.1) # +10% зверху

    # --- Interactive Slots ---

    def on_pie_slice_hovered(self, slice_, state):
        slice_.setExploded(state)
        slice_.setLabelVisible(state or slice_.value() > 0) # Keep visible if set in logic, or enforce on hover
        
        # Optional: Show percentage on hover
        if state:
            original_label = slice_.label().split(" (")[0] # remove old percentage if any
            percentage = slice_.percentage() * 100
            slice_.setLabel(f"{original_label} ({percentage:.1f}%)")
        else:
            # Restore original label format (simplified)
            # A more robust way would be storing the original text in slice.data()
            label_parts = slice_.label().split(" (")
            slice_.setLabel(label_parts[0])

    def on_bar_hovered(self, status, index):
        if status:
            val = self.bar_set.at(index)
            QToolTip.showText(QCursor.pos(), f"Витрати: {val:.2f} ₴")
        else:
            QToolTip.hideText()
