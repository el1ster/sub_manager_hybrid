# --- Dark Theme ---
DARK_THEME_QSS = """
QWidget {
    background-color: #212121;
    color: #FAFAFA;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QMainWindow {
    background-color: #313131;
}
QTableView {
    border: 1px solid #424242;
    gridline-color: #424242;
}
QHeaderView::section {
    background-color: #3c3c3c;
    padding: 4px;
    border: 1px solid #424242;
    font-weight: bold;
}
QGroupBox {
    background-color: #2c2c2c;
    border: 1px solid #424242;
    border-radius: 5px;
    margin-top: 1ex;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 3px;
    left: 10px;
}
QPushButton {
    background-color: #03A9F4; /* Light Blue */
    color: #212121;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #29B6F6;
}
QPushButton:disabled {
    background-color: #424242;
    color: #757575;
}
QLineEdit, QDoubleSpinBox, QComboBox, QDateEdit {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    padding: 5px;
    border-radius: 4px;
}
QTabWidget::pane {
    border: 1px solid #424242;
}
QTabBar::tab {
    background: #3c3c3c;
    border: 1px solid #424242;
    padding: 8px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    color: #BDBDBD;
}
QTabBar::tab:selected {
    background: #2c2c2c;
    border-bottom-color: #2c2c2c;
    color: #FFFFFF;
}
QStatusBar {
    background-color: #3c3c3c;
}
QTextEdit { /* For server logs */
    background-color: #1e1e1e;
    color: #00ff00;
}
"""
