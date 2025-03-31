import sys
import os
import warnings
import pickle
from datetime import datetime
from typing import List, Union
import pandas as pd
from PyQt6 import QtWidgets, uic

# Suppress specific warnings related to pandas
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")


def date_converter(date_string: str) -> str:
    """
    Convert a date string in the format 'Wed Mar 03 2021' to 'YYYY/MM/DD'.
    """
    return datetime.strptime(date_string, "%a %b %d %Y").strftime("%Y/%m/%d")


class Helpers:
    def __init__(self) -> None:
        self.drive_letters = self.get_drive_letters()

    @staticmethod
    def get_drive_letters() -> List[str]:
        """Return a list of available drive letters."""
        return [
            f"{chr(drive)}:\\"
            for drive in range(65, 91)
            if os.path.exists(f"{chr(drive)}:\\")
        ]

    def get_company_folders(self,
                            directory_path:
                            str) -> Union[List[str], bool]:
        """Return a list of company folders in the specified directory."""
        directory_path = os.path.join(directory_path,
                                      "bank_recon"
                                      )
        return (
            [
                d
                for d in os.listdir(directory_path)
                if os.path.isdir(os.path.join(directory_path, d))
            ]
            if os.path.exists(directory_path)
            else False
        )


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        """Initialize the main window and UI components."""
        super().__init__()
        uic.loadUi("basic.ui", self)
        self.helper = Helpers()
        self.setup_vars()
        self.show()

    def setup_vars(self):
        """Set up UI variable connections."""
        self.btn_close.clicked.connect(self.closeApplication)
        self.btn_maximize_restore.clicked.connect(self.toggleMaximize)
        self.btn_minimize.clicked.connect(self.toggleMinimize)

        self.drive_combo_box.addItems(self.helper.drive_letters)
        self.drive_box_change(0)
        self.drive_combo_box.currentIndexChanged.connect(self.drive_box_change)
        self.create_csv_button.clicked.connect(self.create_csv)

    def drive_box_change(self, index: int):
        """Update the company box based on the selected drive."""
        drive_letter = (
            self.drive_combo_box.itemText(index)
            or self.drive_combo_box.currentText()
        )
        companies = self.helper.get_company_folders(drive_letter)
        self.company_box.clear()
        (
            self.company_box.addItems(companies)
            if companies
            else self.status_box.setText("STATUS: No Company Folder Found")
        )
        self.status_box.setText(
            f"STATUS: {len(companies)} company found"
            if companies
            else "STATUS: No Company Folder Found"
        )

    def closeApplication(self):
        """Close the application."""
        self.close()

    def toggleMaximize(self):
        """Toggle between maximizing and restoring the window."""
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def toggleMinimize(self):
        """Minimize the window."""
        self.showNormal() if self.isMinimized() else self.showMinimized()

    def create_csv(self):
        """Create a CSV file based on selected date range and company."""
        start = self.start_date_widget.selectedDate().toString("yyyy/MM/dd")
        end = self.end_date_widget.selectedDate().toString("yyyy/MM/dd")

        self.progressBar.setVisible(True)
        self.progressBar.setValue(10)
        company = self.company_box.currentText()
        directory_path = os.path.join(
            self.drive_combo_box.currentText(), "bank_recon", company
        )

        handler = MainHandler(start, end, company, directory_path)
        handler.run()
        self.progressBar.setValue(100)


class MainHandler:
    def __init__(self, start: str,
                 end: str, company: str,
                 directory_path: str) -> None:
        self.company = company
        self.start = datetime.strptime(start, "%Y/%m/%d")
        self.end = datetime.strptime(end, "%Y/%m/%d")

        if self.company == "GW":
            self.process_gw_data(directory_path)
        else:
            self.load_and_filter_data(directory_path)

    def process_gw_data(self, directory_path: str):
        """Process data for the 'GW' company."""
        GL = pickle.load(open(f"{directory_path}/GW.pkl", "rb"))
        GL["YEAR"] = pd.DatetimeIndex(GL["trndate"]).year
        GL["MONTH"] = pd.DatetimeIndex(GL["trndate"]).month
        BANK_RECON_GL = GL.loc[
            (GL["MONTH"] <= 12)
            & (GL["subacct"] == "1001")
            & (GL["trndate"].between(self.start, self.end))
        ][["trndate", "trnno", "subacct", "payee", "dr_amt", "cr_amt", "net_"]]
        BANK_RECON_GL.to_csv(f"{self.company}_gl_data.csv", index=False)

    def load_and_filter_data(self, directory_path: str):
        """Load and filter transaction data."""
        TRN_COLUMNS = [
            "TRNTYPE",
            "TRNNO",
            "TRNDATE",
            "ACCTNO",
            "ACCTNAME",
            "SUBACCT",
            "SUBNAME",
            "DEPT_NO",
            "DEPT_NAME",
            "DR_AMT",
            "CR_AMT",
            "NAME",
            "ATCI",
            "ATCC",
            "DE",
            "DSN",
            "PayType",
        ]
        TRM_COLUMNS = [
            "TRNTYPE",
            "TRNNO",
            "TRNDATE",
            "REMARK",
            "OTHER_01",
            "OTHER_02",
            "OTHER_03",
            "NAME",
        ]
        TRN_CHEQUE_COLUMNS = [
            "TRNTYPE",
            "TRNNO",
            "TRNDATE",
            "PAYEE",
            "ACCTNO",
            "CHEQUENO",
            "CHEQUEDATE",
            "AMOUNT",
        ]

        self.TRN = pickle.load(open(
            f"{directory_path}/TRN.pkl", "rb"
        ))[TRN_COLUMNS]
        self.TRM = pickle.load(open(
            f"{directory_path}/TRM.pkl", "rb"
        ))[TRM_COLUMNS]
        self.TRN_CHEQUE = pickle.load(open(
            f"{directory_path}/TRN_CHEQUE.pkl", "rb"
        ))[TRN_CHEQUE_COLUMNS]

        self.TRN = self.TRN[
            self.TRN["TRNDATE"].between(self.start, self.end)
        ].sort_values(by=["TRNDATE", "TRNNO"])
        self.TRM = self.TRM[
            self.TRM["TRNDATE"].between(self.start, self.end)
        ].sort_values(by=["TRNDATE", "TRNNO"])
        self.TRN_CHEQUE = self.TRN_CHEQUE[
            self.TRN_CHEQUE["TRNDATE"].between(self.start, self.end)
        ].sort_values(by=["TRNDATE", "TRNNO"])

    def run(self):
        """Execute the main processing logic."""
        GL1 = pd.merge(
            self.TRN,
            self.TRM,
            on=["TRNNO", "TRNDATE"],
            how="left",
            suffixes=("", "_TRM"),
        )
        GL1["PAYEE"] = GL1["OTHER_01"].combine_first(GL1["NAME_TRM"])
        GL1["YEAR"] = GL1["TRNDATE"].dt.year
        GL1["MONTH"] = GL1["TRNDATE"].dt.month
        GL1["NET_AMT"] = GL1["DR_AMT"] - GL1["CR_AMT"]
        GL1["CASH_TRN_REF"] = GL1.apply(
            lambda x: (
                f"{x['TRNNO']}{x['SUBACCT']}"
                if x["ACCTNO"] == "1001" and x["CR_AMT"] != 0
                else None
            ),
            axis=1,
        )

        GL1.reset_index(inplace=True)
        GL1.rename(columns={"index": "ID"}, inplace=True)

        TRN_CHEQUE_DF = self.TRN_CHEQUE.copy()
        TRN_CHEQUE_DF["CASH_TRN_REF"] = (
                TRN_CHEQUE_DF["TRNNO"] +
                TRN_CHEQUE_DF["ACCTNO"])
        TRN_CHEQUE_DF.reset_index(inplace=True)
        TRN_CHEQUE_DF.rename(columns={"index": "ID_CHK"}, inplace=True)

        GL_With_Check = pd.merge(
            GL1,
            TRN_CHEQUE_DF,
            on=["CASH_TRN_REF", "TRNDATE"],
            how="left",
            suffixes=("", "_CHK"),
        )
        GL_With_Check["Duplicate Entry?"] = GL_With_Check.duplicated(
            subset="ID", keep="first"
        )
        GL_With_Check["Duplicate Cheque Entry?"] = GL_With_Check.duplicated(
            subset="ID_CHK", keep="first"
        )

        GL_With_Check["DR_AMT"] = GL_With_Check["DR_AMT"].where(
            ~GL_With_Check["Duplicate Entry?"], 0
        )
        GL_With_Check["CR_AMT"] = GL_With_Check["CR_AMT"].where(
            ~GL_With_Check["Duplicate Entry?"], 0
        )
        GL_With_Check["AMOUNT"] = (
            GL_With_Check["AMOUNT"]
            .where(~GL_With_Check["Duplicate Cheque Entry?"], 0)
            .fillna(0)
        )
        GL_With_Check["CR_AMT_2"] = GL_With_Check.apply(
            lambda x: (
                x["AMOUNT"]
                if x["AMOUNT"] != 0 or pd.notna(x["CHEQUENO"])
                else x["CR_AMT"]
            ),
            axis=1,
        )
        GL_With_Check["NET_AMT"] = (
                GL_With_Check["DR_AMT"] -
                GL_With_Check["CR_AMT_2"])
        GL_With_Check["TRANSACTION REFERENCE"] = GL_With_Check.apply(
            lambda x:
            x["OTHER_03"]
            if x["TRNTYPE"] == "03"
            else x["CHEQUENO"],
            axis=1
        ).fillna("")

        GL_With_Check["PAYEE"] = GL_With_Check["PAYEE_CHK"].combine_first(
            GL_With_Check["PAYEE"]
        )

        GL = GL_With_Check[GL_With_Check["NET_AMT"] != 0]
        GL.to_csv(f"{self.company}_gl_data.csv", index=False)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    window.setWindowTitle("PyQt-Frameless-Window")
    window.show()
    sys.exit(app.exec())
