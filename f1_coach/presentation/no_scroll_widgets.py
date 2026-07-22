"""Fare tekerliğiyle yanlışlıkla değer değiştirmeyi engelleyen input widget'ları.

Kullanıcı widget'a tıklayıp klavye odağı vermeden fare tekerleğini kaydırırsa,
olay görmezden gelinip sayfanın kendi scroll alanına iletilir.

ÖNEMLİ: Qt'de QSpinBox/QDoubleSpinBox'ın varsayılan odak politikası
WheelFocus'tur — yani fare tekerleği widget'a dokunmadan ÖNCE bile odağı
veriyor, sadece wheelEvent'i override etmek bu yüzden yetersiz kalır (odak
zaten verilmiş olur, hasFocus() kontrolü hep True döner). Bu yüzden
constructor'da odak politikasını StrongFocus'a (yalnızca tıklama/Tab ile
odaklan, tekerlekle değil) düşürüyoruz — çağıran kodun bunu ayrıca
hatırlamasına gerek kalmasın diye.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class NoScrollComboBox(QComboBox):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class NoScrollSpinBox(QSpinBox):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)