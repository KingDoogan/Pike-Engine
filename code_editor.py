import sys
import re
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget, QTextEdit, QAction, QFileDialog, QPushButton, QSplitter
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QBrush, QColor, QPainter, QPainterPath, QPalette, QIcon, QSyntaxHighlighter
from PyQt5.QtCore import Qt, QSize, QRect, QRectF, QObject, QEvent, pyqtSignal
from io import StringIO
import contextlib
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.blue)
        keyword_format.setFontWeight(QFont.Bold)

        keywords = [
            "and", "as", "assert", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "False",
            "finally", "for", "from", "global", "if", "import",
            "in", "is", "lambda", "None", "nonlocal", "not",
            "or", "pass", "raise", "return", "True", "try",
            "while", "with", "yield"
        ]

        self.highlighting_rules = [(re.compile(r'\b' + keyword + r'\b'), keyword_format) for keyword in keywords]

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(Qt.darkGreen)
        self.highlighting_rules.append((re.compile(r'\".*\"'), self.string_format))
        self.highlighting_rules.append((re.compile(r'\'.*\''), self.string_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            iterator = pattern.finditer(text)
            for match in iterator:
                self.setFormat(match.start(), match.end() - match.start(), format)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.init_ui()
        # Set window background color using style sheet
        self.setStyleSheet("color: gray;"
                        "background-color: black;"
                        "selection-color: black;"
                        "selection-background-color: blue;");


    def init_ui(self):
        font = QFont("Courier New", 12)  # Replace with your desired font and size
        self.setFont(font)

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width()
        self.highlight_current_line()
        self.highlighter = PythonHighlighter(self.document())

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num /= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.yellow).lighter(160)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), Qt.lightGray)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, top, self.line_number_area.width(), self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

class CodeEditorApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.editor = CodeEditor()
        self.console = QTextEdit()  # Initialize the console widget
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.console)
        self.splitter.setSizes([300, 100])  # Adjust initial sizes as needed

        self.setCentralWidget(self.splitter)

        self.setWindowTitle("Pike Code Editor")
        self.setGeometry(100, 100, 800, 600)

        self.init_menu_bar() # Initialize the console widget
        self.imported_modules = {}

    def init_console(self):
        self.console = QPlainTextEdit(self)
        self.console.setGeometry(0, 0, 800, 200)  # Adjust the geometry as needed
        self.console.setReadOnly(True)
        self.console.setPlainText("Console output:\n")

        sys.stdout = self.console  # Redirect stdout to the console widget

    def init_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        run_action = QAction("Run", self)  # Add the "Run" action
        run_action.triggered.connect(self.run_code)  # Connect the action to a function
        menubar.addAction(run_action)  # Add the action to the menu bar

    def run_import(self, module_name):
        try:
            module = __import__(module_name)
            self.imported_modules[module_name] = module
            print(f"Imported module: {module_name}")
        except ImportError as e:
            print(f"Error importing module {module_name}: {e}")

    def run_code(self):
        code = self.editor.toPlainText()

        # Execute the code using the imported modules
        for module_name, module in self.imported_modules.items():
            code = f"import {module_name}\n{code}"

        # Redirect stdout to the console widget
        original_stdout = sys.stdout
        with contextlib.redirect_stdout(TextEditRedirect(self.console)):
            try:
                exec(code)  # Execute the code
            except Exception as e:
                print("An error occurred:", e)

        sys.stdout = original_stdout

    def open_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt)", options=options)

        if file_name:
            with open(file_name, "r") as file:
                self.editor.setPlainText(file.read())

    def save_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*);;Text Files (*.txt)", options=options)

        if file_name:
            with open(file_name, "w") as file:
                file.write(self.editor.toPlainText())

class TextEditRedirect:
    def __init__(self, text_edit):
        self.text_edit = text_edit

    def write(self, text):
        self.text_edit.moveCursor(QTextCursor.End)
        self.text_edit.insertPlainText(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    icon = QIcon("icon.ico")
    app.setWindowIcon(icon)
    main_win = CodeEditorApp()
    main_win.show()
    sys.exit(app.exec_())
