#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
from math import ceil
from collections import defaultdict

from utils import *

from PyQt5.QtWidgets import (QApplication, QWidget, QScrollArea, QLabel, QPushButton,
                             QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSize, pyqtSignal, pyqtSlot, QEventLoop

N_QUERY = 5
COVER_SIZE = 150
SEARCH_WINDOW_WIDTH = 1000
SEARCH_WINDOW_HEIGHT = 250
WINDOW_WIDTH = 780
WINDOW_HEIGHT = 480
N_COLS = 4

BACKGROUND_COLOR = '#F7F7F7'
COLOR = '#444'
SCROLL_BAR_STYLE = '''
    QScrollBar:vertical {
         border: 0;
         background: #F7F7F7;
         width: 8px;
         margin: 0;
     }
     QScrollBar::handle:vertical {
         background: #666;
         min-height: 5px;
     }
     QScrollBar::add-line:vertical {
         border: none;
         background: none;
         height: 0px;
     }

     QScrollBar::sub-line:vertical {
         border: none;
         background: none;
     }
     QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
         border: none;
         background: none;
         color: none;
     }

     QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
         background: none;
     }
'''


class main_widget(QWidget):
    def __init__(self, parent=None):
        super(main_widget, self).__init__(parent)

        self._artist_album_dict = defaultdict(set)

        self.setWindowTitle('MusicFilesUI')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet('background-color: {}'.format(BACKGROUND_COLOR))
        self.setAcceptDrops(True)

        vbox = QVBoxLayout(self)
        vbox.addStretch(1)
        pixmap = QPixmap('icons/d&d_icon.png')
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        vbox.addWidget(image_label, alignment=Qt.AlignCenter)
        text_label = QLabel()
        text_label.setText('Drag and drop mp3 files')
        font = QFont()
        font.setPointSize(16)
        text_label.setFont(font)
        text_label.setStyleSheet('color: {}'.format(COLOR))

        vbox.addWidget(text_label, alignment=Qt.AlignCenter)
        vbox.addStretch(1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        file_paths = get_mp3_file_paths(paths)
        new_dict = get_artist_album_dict(file_paths)
        self._artist_album_dict.update(new_dict)

        if len(self._artist_album_dict) != 0:
            self._change_layout()

    def _change_layout(self):
        # clear layout
        QWidget().setLayout(self.layout())

        scroll_widget = QWidget()
        scroll_vbox = QVBoxLayout(scroll_widget)

        self._init_album_layouts()

        for hbox in self._album_layouts:
            hbox.setContentsMargins(0, 0, 0, 10)
            scroll_vbox.addLayout(hbox)

        scroll = QScrollArea()
        scroll.setFixedHeight(WINDOW_HEIGHT)
        bar = scroll.verticalScrollBar()
        bar.setStyleSheet(SCROLL_BAR_STYLE)
        scroll.setWidget(scroll_widget)
        scroll.setAlignment(Qt.AlignCenter)

        vbox = QVBoxLayout(self)
        vbox.addWidget(scroll)
        vbox.setContentsMargins(0, 0, 0, 0)

    def _init_album_layouts(self):
        n_albums = get_n_albums(self._artist_album_dict)
        artists = sorted(list(self._artist_album_dict.keys()), key=str.lower)
        album_widgets = []
        for artist in artists:
            albums = sorted([x for x in self._artist_album_dict[artist]], key=lambda x: str.lower(x[0]))
            for album in albums:
                album_widgets.append(album_widget(artist, album[0], album[1]))

        for i in range(len(album_widgets)):
            for j in range(len(album_widgets)):
                if i == j:
                    continue

                album_widgets[i].cover.begin_search.connect(
                    album_widgets[j].cover.disable
                )
                album_widgets[i].cover.end_search.connect(
                    album_widgets[j].cover.enable
                )

        self._album_layouts = [QHBoxLayout() for i in range(ceil(n_albums / N_COLS))]
        for i, a_widget in enumerate(album_widgets):
            hbox_index = i // N_COLS
            self._album_layouts[hbox_index].addWidget(a_widget, alignment=Qt.AlignTop)


class album_widget(QWidget):
    def __init__(self, artist_name, album_name, album_dir_name, parent=None):
        super(album_widget, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        vbox = QVBoxLayout(self)
        vbox.setSpacing(0)
        vbox.setContentsMargins(10, 10, 10, 0)

        vbox.addStretch(1)

        cover_image_path = os.path.join(album_dir_name, 'cover.jpg')
        self._cover = cover_widget(cover_image_path)
        vbox.addWidget(self._cover, alignment=Qt.AlignCenter)

        self._artist = name_widget(artist_name)
        vbox.addWidget(self._artist, alignment=Qt.AlignCenter)

        self._album = name_widget(album_name)
        vbox.addWidget(self._album, alignment=Qt.AlignCenter)

        vbox.addStretch(1)

    @property
    def cover(self):
        return self._cover

    @property
    def artist(self):
        return self._artist

    @property
    def album(self):
        return self._album

    def sizeHint(self):
        return QSize(COVER_SIZE, 300)

class cover_widget(QWidget):
    begin_search = pyqtSignal()
    end_search = pyqtSignal()

    def __init__(self, cover_file_path, parent=None):
        super(cover_widget, self).__init__(parent)

        self.begin_search.connect(self.disable)
        self.end_search.connect(self.enable)

        self._cover_file_path = cover_file_path

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)

        self._cover_label = QLabel()
        if os.path.exists(cover_file_path):
            pixmap = QPixmap(cover_file_path)
            self._set_cover(pixmap)
        else:
            self._cover_label.setText('No Cover')
            self._cover_label.setAlignment(Qt.AlignCenter)
            font = QFont()
            font.setPointSize(16)
            self._cover_label.setFont(font)
            self._cover_label.setStyleSheet(
                'color: {}; background-color: {}'.format(BACKGROUND_COLOR, COLOR))
        vbox.addWidget(self._cover_label)

    @property
    def cover_file_path(self):
        return self._cover_file_path

    def mousePressEvent(self, event):
        self._search_cover_image(self.parentWidget().artist.name,
                                 self.parentWidget().album.name)

    def _set_cover(self, cover):
        p = cover.scaled(QSize(COVER_SIZE, COVER_SIZE), Qt.KeepAspectRatio)
        self._cover_label.setPixmap(p)

    def _search_cover_image(self, artist_name, album_name):
        search_widget = cover_search_widget(artist_name, album_name)
        search_widget.setWindowFlags(Qt.Tool) # Tool window is alywas on top.
        search_widget.show()

        loop = QEventLoop()
        search_widget.canceled.connect(loop.quit)
        search_widget.finished.connect(loop.quit)
        search_widget.result.connect(self._save_searched_cover)
        self.begin_search.emit()
        search_widget.search()
        loop.exec()
        self.end_search.emit()

        if os.path.exists(self._cover_file_path):
            pixmap = QPixmap(self._cover_file_path)
            self._set_cover(pixmap)

    @pyqtSlot()
    def enable(self):
        self.setEnabled(True)

    @pyqtSlot()
    def disable(self):
        self.setEnabled(False)

    @pyqtSlot(QPixmap)
    def _save_searched_cover(self, cover):
        cover.save(self._cover_file_path)

    def sizeHint(self):
        return QSize(COVER_SIZE, COVER_SIZE)


class name_widget(QWidget):
    def __init__(self, name, parent=None):
        super(name_widget, self).__init__(parent)

        self._name = name
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 5, 0, 0)

        label = QLabel()
        label.setText(name)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        font = QFont()
        font.setPointSize(12)
        label.setFont(font)
        label.setStyleSheet('color: {}'.format(COLOR))
        vbox.addWidget(label)

    @property
    def name(self):
        return self._name

    def sizeHint(self):
        return QSize(COVER_SIZE, 10)


class cover_search_widget(QWidget):
    finished = pyqtSignal()
    canceled = pyqtSignal()
    result = pyqtSignal(QPixmap)
    _arrow_style = 'background-color: {}; border: 0'.format(BACKGROUND_COLOR)
    _button_style = '''
        QPushButton {
            background-color: #888;
            color: #F7F7F7;
            border: 0;
            width: 6em;
            height: 2em;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #666;
            color: #FFFFFF;
        }
        QPushButton:pressed {
            background-color: #444;
            color: #FFFFFF;
        }
    '''

    def __init__(self, artist_name, album_name, parent=None):
        super(cover_search_widget, self).__init__(parent)

        self._artist_name = artist_name
        self._album_name = album_name

        self.setWindowTitle('{}: {}'.format(artist_name, album_name))
        self.resize(SEARCH_WINDOW_WIDTH, SEARCH_WINDOW_HEIGHT)
        self.setStyleSheet('background-color: {}'.format(BACKGROUND_COLOR))

        self._cover_start_index = 1
        self._selected_cover_index = -1
        self._cover_pixmaps = []
        self._cover_resolutions = []

        self._init_layout()
        self.setLayout(self._layout)

        self._set_state_loading()

    def _init_layout(self):
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 30)

        self._init_search_layout()
        self._layout.addLayout(self._search_layout)

        self._init_button_layout()
        self._layout.addLayout(self._button_layout)

    def _init_search_layout(self):
        self._search_layout = QHBoxLayout()
        self._search_layout.setContentsMargins(5, 30, 5, 10)

        left_pixmap = QPixmap('icons/prev_icon.png')
        left_dummy_pixmap = QPixmap('icons/prev_dummy_icon.png')
        self._left_icon = QIcon(left_pixmap)
        self._left_dummy_icon = QIcon(left_dummy_pixmap)
        left = QPushButton('')
        left.setStyleSheet(self._arrow_style)
        left.setIcon(self._left_dummy_icon)
        left.setIconSize(QSize(72, 72))
        self._search_layout.addWidget(left, alignment=Qt.AlignCenter)

        self._search_layout.addStretch(1)

        self._init_cover_layout()
        for cover_layout in self._cover_layouts:
            self._search_layout.addLayout(cover_layout)

        self._search_layout.addStretch(1)

        right_pixmap = QPixmap('icons/next_icon.png')
        right = QPushButton('')
        right.setStyleSheet(self._arrow_style)
        right.setIcon(QIcon(right_pixmap))
        right.setIconSize(QSize(72, 72))
        self._search_layout.addWidget(right, alignment=Qt.AlignCenter)

        for cover_layout in self._cover_layouts:
            left.clicked.connect(cover_layout.itemAt(0).widget().unselected)
            right.clicked.connect(cover_layout.itemAt(0).widget().unselected)
        left.clicked.connect(self._prev)
        right.clicked.connect(self._next)

    def _init_cover_layout(self):
        self._cover_layouts = []
        for i in range(N_QUERY):
            cover = searched_cover_widget()
            resolution_label = QLabel()

            layout = QVBoxLayout()
            layout.addWidget(cover, alignment=Qt.AlignCenter)
            layout.addWidget(resolution_label, alignment=Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)

            self._cover_layouts.append(layout)

        for i in range(len(self._cover_layouts)):
            self._cover_layouts[i].itemAt(0).widget().clicked.connect(lambda x=i: self._set_selected_cover_index(x))
            for j in range(len(self._cover_layouts)):
                if i == j:
                    continue

                self._cover_layouts[i].itemAt(0).widget().clicked.connect(
                    self._cover_layouts[j].itemAt(0).widget().unselected
                )

    def _init_button_layout(self):
        self._button_layout = QHBoxLayout()
        self._button_layout.setContentsMargins(0, 0, 30, 0)
        self._button_layout.addStretch(1)
        ok_button = QPushButton('OK')
        ok_button.setStyleSheet(self._button_style)
        cancel_button = QPushButton('Cancel')
        cancel_button.setStyleSheet(self._button_style)
        self._button_layout.addWidget(ok_button)
        self._button_layout.addWidget(cancel_button)

        ok_button.clicked.connect(self._ok)
        cancel_button.clicked.connect(self._cancel)

    def _set_state_loading(self):
        for cover_layout in self._cover_layouts:
            cover_layout.itemAt(0).widget().setPixmap(QPixmap())
        center_index = N_QUERY // 2
        self._cover_layouts[center_index].itemAt(0).widget().setText('Loading...')

    def search(self):
        pixmaps = download_cover_images(self._artist_name, self._album_name,
                                        self._cover_start_index, N_QUERY)
        for p in pixmaps:
            resolution = p.size()
            self._cover_pixmaps.append(p)
            self._cover_resolutions.append(resolution)

        self._set_state_showing()

    def _set_state_showing(self):
        for i in range(len(self._cover_layouts)):
            pixmap_index = i + self._cover_start_index - 1
            self._cover_layouts[i].itemAt(0).widget().setPixmap(self._cover_pixmaps[pixmap_index])
            width = self._cover_resolutions[pixmap_index].width()
            height = self._cover_resolutions[pixmap_index].height()
            self._cover_layouts[i].itemAt(1).widget().setText('{}x{}'.format(width, height))

    def _show_selected_cover(self):
        for i, cover_layout in enumerate(self._cover_layouts):
            if (self._cover_start_index + i) == self._selected_cover_index:
                cover_layout.itemAt(0).widget().selected()
                
    @pyqtSlot()
    def _set_selected_cover_index(self, cover_layout_index):
        self._selected_cover_index = self._cover_start_index + cover_layout_index - 1

    @pyqtSlot()
    def _prev(self):
        self._cover_start_index = max(1, self._cover_start_index - N_QUERY)
        if self._cover_start_index == 1:
            self._search_layout.itemAt(0).widget().setIcon(self._left_dummy_icon)

        self._set_state_showing()
        self._show_selected_cover()

    @pyqtSlot()
    def _next(self):
        self._cover_start_index += N_QUERY
        if self._cover_start_index > len(self._cover_pixmaps):
            self._set_state_loading()
            self.search()
        else:
            self._set_state_showing()
        self._search_layout.itemAt(0).widget().setIcon(self._left_icon)
        self._show_selected_cover()

    @pyqtSlot()
    def _ok(self):
        if self._selected_cover_index != -1:
            self.result.emit(self._cover_pixmaps[self._selected_cover_index])
            self.finished.emit()
            self.close()

    @pyqtSlot()
    def _cancel(self):
        self.canceled.emit()
        self.close()


class searched_cover_widget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, cover_pixmap=None, parent=None):
        super(searched_cover_widget, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel()
        self._label.setFixedWidth(COVER_SIZE)
        self._label.setFixedHeight(COVER_SIZE)
        self._label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        self._label.setFont(font)
        self._label.setStyleSheet('color: #444')

        if cover_pixmap is not None:
            self.setPixmap(cover_pixmap)

        vbox.addWidget(self._label)

        self.clicked.connect(self.selected)

    def setText(self, text):
        self._label.setText(text)

    def setPixmap(self, pixmap):
        if not pixmap.isNull():
            p = pixmap.scaled(QSize(COVER_SIZE, COVER_SIZE), Qt.KeepAspectRatio)
            self._label.setPixmap(p)
        else:
            self._label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        self.clicked.emit()

    @pyqtSlot()
    def selected(self):
        self._label.setStyleSheet('border: 3px solid #666;')

    @pyqtSlot()
    def unselected(self):
        self._label.setStyleSheet('border: 0px;')


    def sizeHint(self):
        return QSize(COVER_SIZE, COVER_SIZE)


def main():
    app = QApplication(sys.argv)
    w = main_widget()
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':    
    main()
    
# ToDo
# UI (Cover hover, pressed, left and right hover, pressed, ok button if index == -1)
# refactoring (cover widget...)