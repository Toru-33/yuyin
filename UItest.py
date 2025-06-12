from PyQt5.QtWidgets import *
import sys


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setup_ui()

    def setup_ui(self):
        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        vbox = QVBoxLayout(self.widget)

        btu1 = QPushButton('选择单个文件')
        btu2 = QPushButton('选择多个文件')
        btu3 = QPushButton('选择单个目录')

        btu1.clicked.connect(self.Select_a_single_file)
        btu2.clicked.connect(self.Select_multiple_files)
        btu3.clicked.connect(self.Select_a_single_directory)

        vbox.addWidget(btu1)
        vbox.addWidget(btu2)
        vbox.addWidget(btu3)

    # 选择单个文件
    def Select_a_single_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "All Files (*)")
        if file_path:
            print(file_path)

    # 选择多个文件
    def Select_multiple_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "选择文件", "/", "Excel文件 (*.xlsx *xls);;Word文件 (*.docx)")
        if file_paths:
            print(file_paths)

    def Select_a_single_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录", "F:/", QFileDialog.ShowDirsOnly)
        if dir_path:
            print("选择的目录路径：", dir_path)


if __name__ == '__main__':

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
