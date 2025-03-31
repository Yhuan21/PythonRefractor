import pickle
import pandas as pd
from datetime import datetime


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
