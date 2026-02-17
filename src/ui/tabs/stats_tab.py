from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QToolTip, QGroupBox
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PySide6.QtGui import QPainter, QColor, QCursor, QBrush
from PySide6.QtCore import Qt
from src.core.analytics import analytics
from src.database.db_manager import db
from src.core.models import SystemSettings

class StatsTab(QWidget):
    """Віджет для вкладки 'Статистика'."""

    def __init__(self):
        super().__init__()
        
        # Основний лейаут: горизонтальний для двох графіків
        self.layout = QHBoxLayout(self)
        self.bar_categories = [] # Зберігаємо назви місяців для тултіпів
        
        # --- 1. Pie Chart (Категорії) ---
        self.pie_chart_view = self.create_pie_chart()
        self.layout.addWidget(self.pie_chart_view)
        
        # --- 2. Bar Chart (Прогноз) ---
        self.bar_chart_view = self.create_bar_chart()
        self.layout.addWidget(self.bar_chart_view)
        
        # Завантаження даних та теми
        # is_dark передается из MainWindow
        self.is_dark = True # Предполагаем темную тему, так как она принудительная
        self.update_theme(self.is_dark)
        # self.refresh_stats() # update_theme already calls it

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
        self.bar_set.setColor(QColor("#03A9F4")) # Light Blue for Dark Theme
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
            slice_.setLabelBrush(QColor(Qt.GlobalColor.white)) # Принудительно белый текст
            # Оригінальний лейбл (без %) для відображення на графіку
            slice_.setLabel(f"{category}") 
            if amount > 0:
                slice_.setLabelVisible(True)

    def _update_bar_chart(self):
        self.bar_set.remove(0, self.bar_set.count())
        self.axis_x.clear()
        self.bar_categories = [] # Очищуємо список категорій
        
        forecast_data = analytics.get_monthly_forecast(12)
        
        max_val = 0
        
        for date_obj, amount in forecast_data:
            self.bar_set.append(amount)
            month_label = date_obj.strftime("%b %Y")
            self.bar_categories.append(month_label)
            if amount > max_val:
                max_val = amount
                
        self.axis_x.append(self.bar_categories)
        self.axis_y.setRange(0, max_val * 1.1)

    # --- Interactive Slots ---

    def on_pie_slice_hovered(self, slice_, state):
        slice_.setExploded(state)
        if state:
            original_label = slice_.label()
            percentage = slice_.percentage() * 100
            val = slice_.value()
            tip_text = f"{original_label}\n{val:.0f} ₴ ({percentage:.1f}%)"
            QToolTip.showText(QCursor.pos(), tip_text)
        else:
            QToolTip.hideText()

    def on_bar_hovered(self, status, index):
        if status:
            val = self.bar_set.at(index)
            month = self.bar_categories[index] if index < len(self.bar_categories) else ""
            QToolTip.showText(QCursor.pos(), f"{month}\nВитрати: {val:.2f} ₴")
        else:
            QToolTip.hideText()

    def update_theme(self, is_dark: bool):
        """Оновлює кольори графіків відповідно до заданої теми (темна/світла)."""
        bg_color = QColor("#2E2E2E") # Dark background
        text_color = QColor(Qt.GlobalColor.white)
            
        # Apply to Pie Chart
        self.pie_chart_view.chart().setBackgroundBrush(QBrush(bg_color))
        self.pie_chart_view.chart().setTitleBrush(QBrush(text_color))
        self.pie_chart_view.chart().legend().setLabelColor(text_color)
        
        # Apply to Bar Chart
        self.bar_chart_view.chart().setBackgroundBrush(QBrush(bg_color))
        self.bar_chart_view.chart().setTitleBrush(QBrush(text_color))
        self.bar_chart_view.chart().legend().setLabelColor(text_color)
        
        # Axes
        self.axis_x.setLabelsColor(text_color)
        self.axis_y.setLabelsColor(text_color)
        self.axis_y.setTitleBrush(text_color)

        # Перерисовка графиков с новыми цветами
        self.refresh_stats()
