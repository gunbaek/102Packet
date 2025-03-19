from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QComboBox, QTabWidget, QCheckBox, QGridLayout,QMenu,QVBoxLayout,  QHBoxLayout, QMainWindow, QMessageBox, QInputDialog,QPushButton)
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtCore import Qt, QPoint, QThread, Signal  # Add for threading
from pathlib import Path
import os
import sys

import serial.tools.list_ports
import serial  # Add this import for serial communication

class SerialReaderThread(QThread):
    data_received = Signal(bytes)  # Signal to emit received data

    def __init__(self, serial_connection):
        super().__init__()
        self.serial_connection = serial_connection
        self.running = True

    def run(self):
        while self.running:
            if self.serial_connection and self.serial_connection.is_open:
                try:
                    data = self.serial_connection.read(1024)  # Read up to 1024 bytes
                    if data:
                        self.data_received.emit(data)
                except Exception as e:
                    print(f"Error reading from serial port: {e}")

    def stop(self):
        self.running = False
        self.wait()


class TabMonitor(QWidget):
    def __init__(self, title: str):
        super().__init__()

        # Variables
        self._favorite = False
        self.serial_connection = None  # Add a variable to manage the serial connection
        self.serial_reader_thread = None  # Thread for reading serial data

        # Add a label to tab
        self.CBox_Comport = QComboBox()
        self.CBox_Baudrate = QComboBox()
        
        # Add port options
        # Get list of available serial ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.CBox_Comport.addItem(port.device)

        # Connect combobox selection to a function to store the selected port
        self.CBox_Comport.currentTextChanged.connect(self.on_comport_selected)

        # Add baudrate options
        self.CBox_Baudrate.addItem("1200")
        self.CBox_Baudrate.addItem("4800")
        self.CBox_Baudrate.addItem("9600")
        self.CBox_Baudrate.addItem("19200")
        self.CBox_Baudrate.addItem("38400")
        self.CBox_Baudrate.currentTextChanged.connect(self.on_buadrate_selected)
        
        btn_Connect = QPushButton('Connect', self)
        btn_Connect.setCheckable(True)
        btn_Connect.clicked.connect(self.on_connect)
        
        # Add Combobox to widget
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.CBox_Comport)
        self.hbox.addWidget(self.CBox_Baudrate)
        self.hbox.addWidget(btn_Connect)
        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.hbox)
        self.vbox.addStretch(0)

        self.label_received_data = QLabel("Received Data:")  # Label to display received data
        self.vbox.addWidget(self.label_received_data)

        self.setLayout(self.vbox)

    def on_comport_selected(self, port):
        self.selected_port = port
        print(f"Selected port: {self.selected_port}")

    def on_buadrate_selected(self, port):
        self.selected_baudrate = port
        print(f"Selected buadrate: {self.selected_baudrate}")
        
    def on_connect(self):
        source = self.sender()
        if source.text() == "Disconnect":
            # Stop the serial reader thread
            if self.serial_reader_thread:
                self.serial_reader_thread.stop()
                self.serial_reader_thread = None

            # Close the serial connection
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
                print("Disconnected from serial port.")
            source.setText("Connect")
        else:
            # Open the serial connection
            try:
                self.serial_connection = serial.Serial(
                    port=self.selected_port,
                    baudrate=int(self.selected_baudrate),
                    timeout=1
                )
                if self.serial_connection.is_open:
                    print(f"Connected to {self.selected_port} at {self.selected_baudrate} baud.")
                    source.setText("Disconnect")

                    # Start the serial reader thread
                    self.serial_reader_thread = SerialReaderThread(self.serial_connection)
                    self.serial_reader_thread.data_received.connect(self.display_received_data)
                    self.serial_reader_thread.start()
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", f"Failed to connect: {e}")

    def display_received_data(self, data):
        # Convert received data to hex and display it
        hex_data = ' '.join(f'{byte:02X}' for byte in data)
        self.label_received_data.setText(f"Received Data: {hex_data}")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Variables
        self.monitors = 0
        self.last_tab_context_menu = -1

        # Load icons
        self.path = Path(__file__).resolve().parent
        self.playlist_icon = QPixmap(os.path.join(self.path, '../images/playlist.png'))
        
        self.resize(500, 500)
        self.setWindowTitle("102 Packet Sniffer")
        self.setWindowIcon(self.playlist_icon)

        # Create tab widget
        # https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QTabWidget.html
        self.tabs = QTabWidget()

        # Set tabs properties before creating settings tab
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)

        # Create and add playlist tabs
        self.monitors += 1
        tab_title = f"Monitor {self.monitors}"
        self.tabs.addTab(TabMonitor(tab_title), self.playlist_icon, tab_title)

        # Created and add settings tab
#       self.tab_settings = TabSettings(tabs=self.tabs)
#        self.tabs.addTab(self.tab_settings, self.gear_icon, "Settings")

        # Set slots
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.tabBar().currentChanged.connect(self.on_tab_current_changed)
        self.tabs.tabBar().tabBarClicked.connect(self.on_tab_bar_click)
        self.tabs.tabBar().tabBarDoubleClicked.connect(self.on_tab_bar_double_click)
        self.tabs.tabBar().tabCloseRequested.connect(self.on_tab_close_requested)
        self.tabs.tabBar().tabMoved.connect(self.on_tab_moved)
        self.tabs.customContextMenuRequested.connect(self.on_custom_context_menu_request)

        # Create context menu
        self.context_menu = QMenu()
        self.action_tab_create = self.context_menu.addAction("Create")
        self.action_tab_create.triggered.connect(self.on_action_tab_create)
        self.action_tab_rename = self.context_menu.addAction("Rename")
        self.action_tab_rename.triggered.connect(self.on_action_tab_rename)
        self.action_tab_close = self.context_menu.addAction("Close")
        self.action_tab_close.triggered.connect(self.on_action_tab_close)
        self.context_menu.addSeparator()
        self.action_tab_close_all = self.context_menu.addAction("Close all")
        self.action_tab_close_all.triggered.connect(self.on_action_tab_close_all)

        # Add tab widget to layout
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.tabs)
        self.setLayout(self.vbox)
        
        

    def on_tab_current_changed(self, tab_index: int):
        print(f"Tab current change: {tab_index}")

    def on_tab_bar_click(self, tab_index: int):
        print(f"Tab bar click: {tab_index}")

    def on_tab_bar_double_click(self, tab_index: int):
        print(f"Tab bar double click: {tab_index}")

        # Get tab widget
        widget = self.tabs.widget(tab_index)

        # Check if widget is a TabPlaylist
        if isinstance(widget, TabMonitor):
            # Toggle and get favorite to set corresponding tab icon
            widget.toggle_favorite()
            if widget.get_favorite():
                self.tabs.tabBar().setTabIcon(tab_index, self.star_icon)
            else:
                self.tabs.tabBar().setTabIcon(tab_index, self.playlist_icon)

    def on_tab_close_requested(self, tab_index: int):
        print(f"Tab close request: {tab_index}")
        if self.tabs.tabBar().tabText(tab_index) == "Settings":
            QMessageBox.warning(self, "Tab close", "Cannot close settings tab.")
            return

        print(f"Removing tab at index {tab_index}")
        self.tabs.removeTab(tab_index)

    def on_tab_moved(self, tab_index: int):
        print(f"Tab moved: {tab_index}")

    def on_custom_context_menu_request(self, point: QPoint):
        print(f"Context menu request ({point.x()},{point.y()})")

        # Convert mouse click in tab bar to tab index
        tab_index = self.tabs.tabBar().tabAt(point)
        if tab_index < 0:
            return

        # Store tab index opened context menu
        self.last_tab_context_menu = tab_index

        # Get selected tab text
        is_settings_tab = False
        if self.tabs.tabBar().tabText(tab_index) == "Settings":
            is_settings_tab = True

        # Enable close menu on playlist tabs and disable on last settings tab
        if is_settings_tab:
            self.action_tab_rename.setDisabled(True)
            self.action_tab_close.setDisabled(True)
        else:
            self.action_tab_rename.setDisabled(False)
            self.action_tab_close.setDisabled(False)

        # Enable close all menu when playlist tabs available
        if self.tabs.count() <= 1:
            self.action_tab_close_all.setDisabled(True)
        else:
            self.action_tab_close_all.setDisabled(False)

        # Show context menu
        self.context_menu.popup(QCursor.pos())

    def on_action_tab_create(self):
        # Set tab index
        tab_insert_index = 0
        if self.last_tab_context_menu >= 0:
            tab_insert_index = self.last_tab_context_menu

        # Set tab title
        self.monitors += 1
        tab_title = f"Playlist {self.monitors}"

        # Insert new tab
        print(f"Inserting tab \"{tab_title}\"at index {tab_insert_index}")
        self.tabs.insertTab(tab_insert_index, TabMonitor(tab_title), self.playlist_icon, tab_title)

    def on_action_tab_rename(self):
        print(f"Renaming tab at index {self.last_tab_context_menu}")
        tab_text, ok = QInputDialog.getText(self, 'Rename tab', 'Enter a new tab title:')
        if ok:
            self.tabs.tabBar().setTabText(self.last_tab_context_menu, str(tab_text))

    def on_action_tab_close(self):
        print(f"Removing tab at index {self.last_tab_context_menu}")
        self.tabs.removeTab(self.last_tab_context_menu)

    def on_action_tab_close_all(self):
        # Close all tabs except settings tab
        while self.tabs.count() > 1:
            for tab_index in range(0, self.tabs.count()):
                if self.tabs.tabBar().tabText(tab_index) != "Settings":
                    print(f"Removing tab at index {self.last_tab_context_menu}")
                    self.tabs.removeTab(tab_index)
                    # After removing a tab, index and count changes and should restart from index 0
                    break


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())