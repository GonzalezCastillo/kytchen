from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, cast

if TYPE_CHECKING:
    from .cookbook import Cookbook

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QLabel, QWidget

from .views import CoreTableModel, FixTable


class MetricModel(CoreTableModel):
    content: list[str]
    header_names = ["Metric"]
    align = ["left"]
    changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget], cookbook: Cookbook) -> None:
        self.cookbook = cookbook
        super().__init__(parent, cookbook.metrics)

    def get_data(self, row: int, col: int) -> Optional[str]:
        if col == 0:
            return self.content[row]
        return None

    def set_data(self, row: int, col: int, value: Any) -> bool:
        if col != 0 or not self.cookbook.rename_metric(row, value):
            return False
        self.changed.emit()
        return True

    def new_entry(self) -> None:
        context = ""
        while True:
            metric, ok = QInputDialog.getText(
                cast(Optional[QWidget], self.parent()),
                "New metric",
                context
                + "Please enter the name of the new metric (for instance, 'g protein'):",
            )
            if not ok:
                return
            if self.cookbook.add_metric(metric):
                self.changed.emit()
                return
            if metric.strip() == "":
                context = "You cannot provide an empty name.\n"
            else:
                context = f"The metric '{metric.strip()}' already exists.\n"

    def delete_entry(self, row: int) -> None:
        if self.cookbook.delete_metric(row, cast(Optional[QWidget], self.parent())):
            self.changed.emit()


class MetricTable(FixTable):
    model: MetricModel
    ModelClass = MetricModel
    item_name = "metric"
    stretch_widths = [0]

    def __init__(self, cookbook: Cookbook) -> None:
        super().__init__(cookbook)
        self.model.rowsMoved.connect(lambda *args: self.model.changed.emit())

        info = QLabel(
            "Metrics are given per unit of each ingredient and added up "
            "in recipes and meal plans.\n"
            "The first metric is the one shown most prominently. "
        )
        info.setWordWrap(True)
        self.vbox.insertWidget(0, info)
