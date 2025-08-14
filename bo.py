import random
from motion.core import *
import sys
import csv
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QTableWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

from my_interface import Ui_MainWindow

mm = [0, 0, 0, 0, 0, 0]
wp = []

lamp = LedLamp("192.168.56.101")
robot = RobotControl("192.168.2.100")
if robot.connect():
    lamp.setLamp("1111")

    robot.engage()
    if robot.moveToStart():
        lamp.setLamp("1000")
        robot.manualJointMode()
        robot.setJointVelocity([0, 0, 0, 0, 0, 0])
        print(robot.getActualStateOut(), robot.getRobotMode(), robot.getRobotState())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.gripper_count = 0
        self.work_timer = QTimer()
        self.work_timer.timeout.connect(self.update_work_indicator)
        self.work_remaining = 0

        self.slider_timer = QTimer()
        self.slider_timer.timeout.connect(self.reset_sliders_if_idle)
        self.last_slider_time = 0

        self.connect_buttons()
        self.connect_sliders()
        self.init_tables()
        self.setup_indicators()

    def setup_indicators(self):
        self.set_indicator_color(self.ui.textBrowser, "red")
        self.set_indicator_color(self.ui.textBrowser_2, "blue")
        self.set_indicator_color(self.ui.textBrowser_3, "gray")
        self.set_indicator_color(self.ui.textBrowser_4, "gray")

    def set_indicator_color(self, widget, color):
        widget.setStyleSheet(f"background-color: {color}; color: white;")
        widget.repaint()

    def connect_buttons(self):
        self.ui.pushButton.clicked.connect(self.system_off)
        self.ui.pushButton_2.clicked.connect(self.system_pause)
        self.ui.pushButton_3.clicked.connect(self.system_stop)
        self.ui.pushButton_17.clicked.connect(self.play_table)
        self.ui.pushButton_19.clicked.connect(self.save_logs)
        self.ui.pushButton_13.clicked.connect(self.add_3_field)
        self.ui.pushButton_12.clicked.connect(self.delete_row)
        self.ui.pushButton_16.clicked.connect(self.tostart)
        self.ui.pushButton_15.clicked.connect(self.load_from_file)
        self.ui.pushButton_14.clicked.connect(self.save_table_to_csv)
        self.ui.pushButton_4.clicked.connect(self.cart)
        self.ui.pushButton_5.clicked.connect(self.joint)
        self.ui.pushButton_6.clicked.connect(self.gripper)

    def cart(self):
        robot.manualCartMode()
        robot.setCartesianVelocity([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        time.sleep(1.0)

    def joint(self):
        robot.manualJointMode()
        robot.setJointVelocity([-1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        time.sleep(1.0)

    def tostart(self):
        robot.moveToStart()
        robot.manualJointMode()
        robot.setJointVelocity([0, 0, 0, 0, 0, 0])
        row_position = self.ui.tableWidget_3.rowCount()
        self.ui.tableWidget_3.insertRow(row_position)
        start_coords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, self.gripper_count % 2]
        for col, value in enumerate(start_coords):
            item = QTableWidgetItem(str(value))
            self.ui.tableWidget_3.setItem(row_position, col, item)
        global wp
        wp.append(Waypoint([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))

    def connect_sliders(self):
        self.ui.verticalSlider.valueChanged.connect(lambda value: self.slider_moved())
        self.ui.verticalSlider_2.valueChanged.connect(lambda value: self.slider_moved())
        self.ui.verticalSlider_3.valueChanged.connect(lambda value: self.slider_moved())
        self.ui.verticalSlider_4.valueChanged.connect(lambda value: self.slider_moved())
        self.ui.verticalSlider_5.valueChanged.connect(lambda value: self.slider_moved())
        self.ui.verticalSlider_6.valueChanged.connect(lambda value: self.slider_moved())

    def slider_moved(self):
        self.last_slider_time = QtCore.QTime.currentTime().second() + QtCore.QTime.currentTime().msec() / 1000.0
        self.slider_timer.start(100)
        sender = self.sender()
        if sender == self.ui.verticalSlider:
            self.update_table2(0, sender.value())
        elif sender == self.ui.verticalSlider_2:
            self.update_table2(1, sender.value())
        elif sender == self.ui.verticalSlider_3:
            self.update_table2(2, sender.value())
        elif sender == self.ui.verticalSlider_4:
            self.update_table2(3, sender.value())
        elif sender == self.ui.verticalSlider_5:
            self.update_table2(4, sender.value())
        elif sender == self.ui.verticalSlider_6:
            self.update_table2(5, sender.value())

    def reset_sliders_if_idle(self):
        current_time = QtCore.QTime.currentTime().second() + QtCore.QTime.currentTime().msec() / 1000.0
        if current_time - self.last_slider_time > 5.0:
            self.ui.verticalSlider.setValue(0)
            self.ui.verticalSlider_2.setValue(0)
            self.ui.verticalSlider_3.setValue(0)
            self.ui.verticalSlider_4.setValue(0)
            self.ui.verticalSlider_5.setValue(0)
            self.ui.verticalSlider_6.setValue(0)
            self.slider_timer.stop()

    def update_table2(self, column, value):
        global mm
        try:
            ticks = abs(value)
            radians_val = round(value * 3.14159 / 180.0, 4)
            degrees_val = abs(value)
            temp_val = abs(robot.getActualTemperature())

            row_labels = [item.text().lower() for item in [
                self.ui.tableWidget_2.verticalHeaderItem(0),
                self.ui.tableWidget_2.verticalHeaderItem(1),
                self.ui.tableWidget_2.verticalHeaderItem(2),
                self.ui.tableWidget_2.verticalHeaderItem(3)
            ]]

            for row_idx, label in enumerate(row_labels):
                if label == "тики":
                    display_value = str(ticks)
                elif label == "радианы":
                    display_value = str(radians_val)
                elif label == "градусы":
                    display_value = str(degrees_val)
                elif label == "температура":
                    display_value = str(temp_val)
                else:
                    display_value = str(value)

                item = QTableWidgetItem(display_value)
                self.ui.tableWidget_2.setItem(row_idx, column, item)

            mm = [0, 0, 0, 0, 0, 0]
            mm[column] = value / 10.0
            robot.setJointVelocity(mm)

            self.log_message(f"Updated motor {column+1} with value {value}")

        except Exception as e:
            self.log_message(f"Error updating table: {str(e)}")

    def play_table(self):
        global wp
        row_count = self.ui.tableWidget_3.rowCount()
        if row_count == 0:
            self.log_message("No points to play")
            return

        self.work_remaining = row_count * 5

        self.set_indicator_color(self.ui.textBrowser, "gray")
        self.set_indicator_color(self.ui.textBrowser_2, "gray")
        self.set_indicator_color(self.ui.textBrowser_3, "green")
        self.set_indicator_color(self.ui.textBrowser_4, "gray")

        print('started')
        print(wp, len(wp))
        robot.moveToPointL(wp)
        self.work_timer.start(1000)
        self.log_message(f"Started playing {row_count} points")

    def update_work_indicator(self):
        self.work_remaining -= 1
        current_color = "green" if self.work_remaining % 2 else "lime"
        self.set_indicator_color(self.ui.textBrowser_3, current_color)

        if self.work_remaining <= 0:
            self.work_timer.stop()
            self.system_off()
            self.log_message("Work complete")

    def add0(self):
        try:
            current_row = self.ui.tableWidget_3.rowCount()
            self.ui.tableWidget_3.insertRow(current_row)
            for col in range(4):
                value = 0 if col < 3 else self.gripper_count % 2
                item = QTableWidgetItem(str(value))
                self.ui.tableWidget_3.setItem(current_row, col, item)
            self.log_message("Added zero point")
        except Exception as e:
            self.log_message(f"Error adding point: {str(e)}")

    def gripper(self):
        self.gripper_count += 1
        if self.gripper_count % 2 == 1:
            self.ui.pushButton_6.setText("On")
            self.log_message("Gripper turned On")
            robot.toolON()
            time.sleep(0.25)
        else:
            self.ui.pushButton_6.setText("Off")
            self.log_message("Gripper turned Off")
            robot.toolOFF()
            time.sleep(0.25)

    def add_3_field(self):
        global wp
        try:
            coords = robot.getToolPosition()
            current_row = self.ui.tableWidget_3.rowCount()
            self.ui.tableWidget_3.insertRow(current_row)
            values = list(coords) + [self.gripper_count % 2]
            wp.append(Waypoint(list(coords)))

            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                self.ui.tableWidget_3.setItem(current_row, col, item)

            self.log_message(f"Added point: {values}")
        except Exception as e:
            self.log_message(f"Error adding point: {str(e)}")

    def delete_row(self):
        global wp
        try:
            self.ui.tableWidget_3.setRowCount(0)
            wp = []
            self.log_message("Cleared all points from table")
        except Exception as e:
            self.log_message(f"Error clearing table: {str(e)}")

    def init_tables(self):
        pass

    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - {message}"
        print(log_entry)
        self.ui.plainTextEdit_10.appendPlainText(log_entry)

    def save_table_to_csv(self):
        filename = self.ui.textEdit_2.toPlainText().strip() or "untitled.csv"
        if not filename.endswith('.csv'):
            filename += '.csv'

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save CSV File", filename, "CSV Files (*.csv)"
        )
        if not filepath:
            self.log_message("CSV save cancelled")
            return

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = [self.ui.tableWidget_3.horizontalHeaderItem(col).text()
                          for col in range(self.ui.tableWidget_3.columnCount())]
                writer.writerow(headers)

                for row in range(self.ui.tableWidget_3.rowCount()):
                    row_data = [
                        self.ui.tableWidget_3.item(row, col).text() if self.ui.tableWidget_3.item(row, col) else ""
                        for col in range(self.ui.tableWidget_3.columnCount())
                    ]
                    writer.writerow(row_data)
            self.log_message(f"Saved table to {filepath}")
        except Exception as e:
            self.log_message(f"Error saving CSV: {str(e)}")

    def load_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not filepath:
            self.log_message("File load cancelled")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, None)

                for row in reader:
                    if len(row) < 6:
                        continue
                    try:
                        coords = [float(x) for x in row[:6]]
                        gripper_val = int(row[6]) if len(row) > 6 else self.gripper_count % 2
                    except:
                        continue

                    table_row = self.ui.tableWidget_3.rowCount()
                    self.ui.tableWidget_3.insertRow(table_row)
                    for col, value in enumerate(row[:7]):
                        item = QTableWidgetItem(value)
                        self.ui.tableWidget_3.setItem(table_row, col, item)

                    global wp
                    wp.append(Waypoint(coords))

            self.log_message(f"Loaded trajectory from {filepath}")
        except Exception as e:
            self.log_message(f"Failed to load file: {str(e)}")

    def save_logs(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"log_{timestamp}.txt"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", default_filename, "Text Files (*.txt);;All Files (*)"
        )
        if not filepath:
            self.log_message("Log save cancelled")
            return

        try:
            log_content = self.ui.plainTextEdit_10.toPlainText()
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"=== Лог робота ===\n")
                f.write(f"Сохранено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'-'*50}\n")
                f.write(log_content)
            self.log_message(f"Сохранено в {filepath}")
        except Exception as e:
            self.log_message(f"Неудача: {str(e)}")

    def system_off(self):
        self.set_indicator_color(self.ui.textBrowser, "red")
        self.set_indicator_color(self.ui.textBrowser_2, "blue")
        self.set_indicator_color(self.ui.textBrowser_3, "gray")
        self.set_indicator_color(self.ui.textBrowser_4, "gray")
        self.work_timer.stop()
        self.log_message("System turned OFF")

    def system_pause(self):
        self.set_indicator_color(self.ui.textBrowser, "gray")
        self.set_indicator_color(self.ui.textBrowser_2, "gray")
        self.set_indicator_color(self.ui.textBrowser_3, "gray")
        self.set_indicator_color(self.ui.textBrowser_4, "orange")
        self.work_timer.stop()
        self.log_message("System PAUSED")

    def system_stop(self):
        self.set_indicator_color(self.ui.textBrowser, "red")
        self.set_indicator_color(self.ui.textBrowser_2, "gray")
        self.set_indicator_color(self.ui.textBrowser_3, "gray")
        self.set_indicator_color(self.ui.textBrowser_4, "gray")
        self.work_timer.stop()
        self.log_message("System STOPPED")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
