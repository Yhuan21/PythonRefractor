from datetime import datetime
import os
import json
from typing import List, Union

with open("config.json", "r") as file:
    config = json.load(file)


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
        directory_path = (config.get("databases", {})
                          .get("CURRENT", directory_path))
        return (
            [
                d
                for d in os.listdir(directory_path)
                if os.path.isdir(os.path.join(directory_path, d))
            ]
            if os.path.exists(directory_path)
            else False
        )


__all__ = ["Helpers", "config"]
