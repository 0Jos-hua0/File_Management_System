from PyQt5.QtWidgets import QPushButton

class CustomButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        # Custom styling or behavior can be added here
