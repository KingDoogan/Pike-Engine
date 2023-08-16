import sys
import pygame
import json  # Import the json module
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QDialog, QDockWidget, QScrollArea, QMenu, QAction, QLabel, QFileDialog  # Include QFileDialog
from PyQt5.QtGui import QPainter, QColor, QIcon
from PyQt5.QtCore import Qt, QRect
from pygame.locals import QUIT

pygame.init()

WHITE = (255, 255, 255)
RED = (255, 0, 0)

class GameObject:
    def __init__(self, color, rect):
        self.color = color
        self.rect = rect

class GameArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.objects = []
        self.cameras = []
        self.clicked_object = None
        self.offset = None
        self.selected_label = None
        self.layout = QVBoxLayout(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        for obj in self.objects:
            rect = QRect(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height)
            painter.fillRect(rect, QColor(*obj.color))

        for camera in self.cameras:
            painter.setPen(QColor(0, 0, 255))
            camera_rect = QRect(camera.x, camera.y, camera.width, camera.height)
            painter.drawRect(camera_rect)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.pos().x(), event.pos().y()
            for obj in self.objects:
                if obj.rect.collidepoint(x, y):
                    self.clicked_object = obj
                    self.offset = (x - obj.rect.x, y - obj.rect.y)
                    break
            else:
                self.clicked_object = None

    def mouseMoveEvent(self, event):
        if self.clicked_object:
            x, y = event.pos().x(), event.pos().y()
            self.clicked_object.rect.x = x - self.offset[0]
            self.clicked_object.rect.y = y - self.offset[1]
            self.update()

    def add_camera(self):
        screen_center = self.rect().center()
        camera = pygame.Rect(screen_center.x(), screen_center.y(), 200, 150)
        self.cameras.append(camera)
        self.update()

    def add_static_object(self):
        if not pygame.get_init():
            pygame.init()
            
        x, y = pygame.mouse.get_pos()
        rect = pygame.Rect(x, y, 50, 50)
        self.objects.append(GameObject(RED, rect))
        self.update()

    def set_selected_label(self, index):
        self.clear_selected_labels()
        self.selected_label = index
        if self.selected_label is not None:
            if 0 <= self.selected_label < self.layout.count():
                layout_item = self.layout.itemAt(self.selected_label)
                if layout_item:
                    widget = layout_item.widget()
                    if widget:
                        widget.set_selected(True)
                    else:
                        print("Widget not found for layout item.")
                else:
                    print("Layout item not found.")

    def clear_selected_labels(self):
        for index in range(self.layout.count()):
            layout_item = self.layout.itemAt(index)
            if layout_item:
                widget = layout_item.widget()
                if widget:
                    widget.set_selected(False)
        self.selected_label = None

    def serialize_objects(self):
        serialized_objects = []
        for obj in self.objects:
            serialized_objects.append({
                "color": obj.color,
                "rect": (obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height)
            })
        for camera in self.cameras:
            serialized_objects.append({
                "color": (0, 0, 255),  # Use a consistent color for cameras
                "rect": (camera.x, camera.y, camera.width, camera.height)
            })
        return serialized_objects

    def deserialize_objects(self, serialized_objects):
        self.objects.clear()  # Clear existing objects
        self.cameras.clear()  # Clear existing cameras
        for obj_data in serialized_objects:
            color = obj_data["color"]
            rect_data = obj_data["rect"]
            rect = pygame.Rect(*rect_data)  # Create a pygame.Rect object
            if color == (0, 0, 255):
                self.cameras.append(rect)  # Add camera
            else:
                self.objects.append(GameObject(color, rect))  # Add regular object
        self.update()
            

class ListItem(QWidget):
    def __init__(self, game_area, obj, index, parent=None):
        super().__init__(parent)
        self.game_area = game_area
        self.obj = obj
        self.index = index

        self.layout = QVBoxLayout(self)
        self.label = QLabel("Object", self)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.label.setMouseTracking(True)
        self.label.setStyleSheet("QLabel { background-color: transparent; }")
        self.label.mousePressEvent = lambda event: self.select_label()

    def show_context_menu(self, point):
        menu = QMenu(self)
        add_component_action = QAction("Add Component", self)
        add_component_action.triggered.connect(self.add_component)
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_object)
        menu.addAction(add_component_action)
        menu.addAction(delete_action)
        menu.exec_(self.mapToGlobal(point))

    def add_component(self):
        print("Add Component action triggered")

    def delete_object(self):
        if self.obj in self.game_area.objects:
            self.game_area.objects.remove(self.obj)
        elif self.obj in self.game_area.cameras:
            self.game_area.cameras.remove(self.obj)
        self.deleteLater()
        self.game_area.update()

    def select_label(self):
        self.game_area.set_selected_label(self.index)

    def set_selected(self, selected):
        if selected:
            self.label.setStyleSheet("QLabel { background-color: lightblue; }")
        else:
            self.label.setStyleSheet("QLabel { background-color: transparent; }")


class ContainerWindow(QDialog):
    def __init__(self, game_area, parent=None):
        super().__init__(parent, Qt.WindowTitleHint)
        self.setWindowTitle("Game Objects")
        self.setGeometry(100, 100, 400, 300)
        self.game_area = game_area
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

    def add_camera(self):
        self.game_area.add_camera()
        self.add_list_item(len(self.game_area.cameras) - 1, "Camera")

    def add_static_object(self):
        self.game_area.add_static_object()
        self.add_list_item(len(self.game_area.objects) - 1, "Static Object")

    def add_list_item(self, index, label_text):
        obj = None
        if label_text == "Camera":
            obj = self.game_area.cameras[index]
        elif label_text == "Static Object":
            obj = self.game_area.objects[index]
        item = ListItem(self.game_area, obj, index)
        item.label.setText(label_text)
        self.layout.addWidget(item)
        item.label.mousePressEvent = lambda event: self.select_label(item)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        add_camera_action = QAction("Add Camera", self)
        add_camera_action.triggered.connect(self.add_camera)
        add_static_object_action = QAction("Add Static Object", self)
        add_static_object_action.triggered.connect(self.add_static_object)
        menu.addAction(add_camera_action)
        menu.addAction(add_static_object_action)
        menu.exec_(event.globalPos())

    def select_label(self, item):
        self.game_area.set_selected_label(item.index)
        self.game_area.clear_selected_labels()
        item.set_selected(True)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pike Engine")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)
        self.game_area = GameArea(self.central_widget)
        self.layout.addWidget(self.game_area)

        self.play_button = QPushButton("Play", self.central_widget)
        self.play_button.clicked.connect(self.start_game)
        self.layout.addWidget(self.play_button)

        self.dock_container = QDockWidget("Game Objects", self)
        self.container_window = ContainerWindow(self.game_area, self.dock_container)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.container_window)
        self.scroll_area.setWidgetResizable(True)

        self.dock_container.setWidget(self.scroll_area)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_container)
        self.dock_container.setVisible(True)

        self.game_objects = []
        self.init_menu_bar()  # Initialize the menu bar

    def init_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")  # Create a "File" menu
        edit_menu = menu_bar.addMenu("Edit")

        new_project_action = QAction("New Project", self)
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)

        save_project_action = QAction("Save Project", self)
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)

        load_project_action = QAction("Load Project", self)
        load_project_action.triggered.connect(self.load_project)
        file_menu.addAction(load_project_action)

        edit_project_action = QAction("Add Component", self)
        edit_project_action.triggered.connect(self.edit_project)
        edit_menu.addAction(edit_project_action)

    def new_project(self):
        print("New Project action triggered")

    def serialize_state(self):
        state = {
            "game_objects": self.game_area.serialize_objects(),
            "cameras": self.game_area.cameras  # Serialize cameras directly
            # Add more data as needed
        }
        return state

    def save_project(self):
        state = self.serialize_state()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "Pik Files (*.pik);;All Files (*)")
        if file_path:
            with open(file_path, "w") as pik_file:
                json.dump(state, pik_file, indent=4, cls=CustomJSONEncoder)

    def load_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "Pik Files (*.pik);;All Files (*)")
        if file_path:
            with open(file_path, "r") as pik_file:
                state = json.load(pik_file)
                self.game_area.deserialize_objects(state.get("game_objects", []))
                self.game_area.cameras = [pygame.Rect(*rect_data) for rect_data in state.get("cameras", [])]

    def deserialize_state(self, state):
        self.deserialize_objects(state.get("game_objects", []))
        self.cameras = [pygame.Rect(*rect_data) for rect_data in state.get("cameras", [])]
        self.update()

    def edit_project(self):
        print("New edit action triggered")

    def start_game(self):
        self.play_game()

    def play_game(self):
        pygame.init()

        screen = pygame.display.set_mode((800, 600))
        clock = pygame.time.Clock()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False

            screen.fill(WHITE)

            for camera in self.game_area.cameras:
                camera_rect = pygame.Rect(camera.x, camera.y, camera.width, camera.height)
                for obj in self.game_area.objects:
                    rect = pygame.Rect(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height)
                    if camera_rect.colliderect(rect):
                        pygame.draw.rect(screen, obj.color, rect.move(-camera_rect.left, -camera_rect.top))

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()

    def serialize_objects(self):
        serialized_objects = []
        for obj in self.objects:
            serialized_objects.append({
                "type": "object",
                "color": obj.color,
                "rect": (obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height)
            })
        for camera in self.cameras:
            serialized_objects.append({
                "type": "camera",
                "rect": (camera.x, camera.y, camera.width, camera.height)
            })
        return serialized_objects

    def deserialize_objects(self, serialized_objects):
        self.objects.clear()
        self.cameras.clear()
        for obj_data in serialized_objects:
            obj_type = obj_data.get("type")
            rect_data = obj_data["rect"]
            rect = pygame.Rect(*rect_data)
            if obj_type == "camera":
                self.cameras.append(rect)
            elif obj_type == "object":
                color = obj_data["color"]
                self.objects.append(GameObject(color, rect))
        self.update()

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pygame.Rect):
            return obj.topleft + obj.size
        return super().default(obj)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon = QIcon("icon.ico")
    app.setWindowIcon(icon)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
