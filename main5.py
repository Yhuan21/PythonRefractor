import sys
from PyQt6 import QtWidgets
from ui.ui import Ui
import warnings

# Suppress specific warnings related to pandas
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    window.setWindowTitle("PyQt-Frameless-Window")
    window.show()
    sys.exit(app.exec())
