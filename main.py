import os
import sys
from PyQt5.QtWidgets import QApplication
from gui.window import MainWindow


def main():
    # Disable Qt accessibility logs that can spam the console on some setups
    os.environ.setdefault("QT_ACCESSIBILITY", "0")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
