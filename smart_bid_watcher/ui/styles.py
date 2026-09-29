APP_STYLE = """
QWidget {
    color: #17211B;
    font-family: "Segoe UI", "Malgun Gothic";
    font-size: 13px;
}
QMainWindow, QDialog { background: #F5F7F5; }
QFrame#Header { background: #163A2A; border-radius: 14px; }
QLabel#AppTitle { color: #FFFFFF; font-size: 22px; font-weight: 700; }
QLabel#AppSubtitle { color: #BCD5C6; font-size: 12px; }
QFrame#Card { background: #FFFFFF; border: 1px solid #DFE6E1; border-radius: 12px; }
QLabel#SectionTitle { font-size: 15px; font-weight: 700; color: #1E2B23; }
QLabel#Muted { color: #68756D; font-size: 12px; }
QLabel#StatusPill {
    background: #E6F5EC; color: #17633B; border-radius: 10px;
    padding: 5px 10px; font-size: 12px; font-weight: 700;
}
QLineEdit, QPlainTextEdit, QComboBox {
    background: #FAFCFA; border: 1px solid #CED8D1; border-radius: 8px;
    padding: 8px; selection-background-color: #25A55F;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border: 2px solid #25A55F; }
QPushButton {
    background: #EDF2EE; border: 1px solid #D3DDD6; border-radius: 8px;
    padding: 9px 14px; font-weight: 600;
}
QPushButton:hover { background: #E3EBE6; }
QPushButton:pressed { background: #D9E4DD; }
QPushButton#Primary {
    background: #1F9D58; color: white; border: 1px solid #1F9D58;
}
QPushButton#Primary:hover { background: #18874B; }
QPushButton#Danger { color: #A13A3A; }
QPushButton:disabled { color: #94A097; background: #EEF1EF; border-color: #E3E7E4; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QListWidget {
    background: #FFFFFF; border: 1px solid #DFE6E1; border-radius: 9px;
    outline: none;
}
QListWidget::item { padding: 9px; border-bottom: 1px solid #EEF2EF; }
QListWidget::item:selected { background: #E8F6ED; color: #173C28; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: #17211B; color: white; border: none; padding: 5px; }
"""
