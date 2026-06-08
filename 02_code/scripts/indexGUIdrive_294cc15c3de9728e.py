import sys
import json
import os
from PyQt6.QtCore import QSortFilterProxyModel
from PyQt6.QtWidgets import (
	QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
	QTreeView, QListWidget, QListWidgetItem, QPushButton, QInputDialog,
	QMessageBox, QMenu, QTabWidget, QSplitter, QAbstractItemView,
	QLabel, QLineEdit
)
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QFileSystemModel, QAction


class FileSystemModelWithCheckboxes(QFileSystemModel):
	"""Модель файловой системы (заглушка, используем контекстное меню)"""
	pass


class CategoryListWidget(QListWidget):
	"""Список категорий с поддержкой клика"""
	def __init__(self, category_type, parent=None):
		super().__init__(parent)
		self.category_type = category_type
		self.main_window = parent
		self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.itemClicked.connect(self.on_item_clicked)

	def on_item_clicked(self, item):
		if self.main_window:
			self.main_window.show_category_files(self.category_type, item.text())


class FileListWidget(QListWidget):
	"""Список файлов, принадлежащих категории, с удалением по правой кнопке"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(self.show_context_menu)
		self.category_type = None
		self.category_name = None
		self.main_window = None

	def show_context_menu(self, position):
		menu = QMenu()
		remove_action = QAction("Удалить из категории", self)
		remove_action.triggered.connect(self.remove_selected_file)
		menu.addAction(remove_action)
		menu.exec(self.viewport().mapToGlobal(position))

	def remove_selected_file(self):
		current = self.currentItem()
		if current and self.main_window:
			self.main_window.remove_file_from_category(self.category_type, self.category_name, current.text())


class MainWindow(QMainWindow):
	def __init__(self, json_path="index.json", root_path="E:/Jericho"):
		super().__init__()
		self.json_path = json_path
		self.root_path = root_path
		self.index_data = self.load_index()
		self.category_lists = {}	  # будет хранить списки категорий для каждой вкладки
		self.category_file_lists = {} # будет хранить списки файлов для каждой вкладки
		self.initUI()

	def load_index(self):
		if os.path.exists(self.json_path):
			with open(self.json_path, 'r', encoding='utf-8') as f:
				return json.load(f)
		else:
			return {"PROJECTS": {}, "SUBJECTS": {}}

	def save_index(self):
		with open(self.json_path, 'w', encoding='utf-8') as f:
			json.dump(self.index_data, f, ensure_ascii=False, indent=2)

	def initUI(self):
		self.setWindowTitle("Иерихон: редактор связей файлов")
		self.setGeometry(100, 100, 1200, 700)

		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		main_layout = QHBoxLayout(central_widget)

		splitter = QSplitter(Qt.Orientation.Horizontal)
		main_layout.addWidget(splitter)

		# Левая панель: дерево файлов
		left_panel = QWidget()
		left_layout = QVBoxLayout(left_panel)
		left_layout.setContentsMargins(0, 0, 0, 0)

		self.search_edit = QLineEdit()
		self.search_edit.setPlaceholderText("Поиск файлов...")
		self.search_edit.textChanged.connect(self.filter_files)
		left_layout.addWidget(self.search_edit)

		# Модель файловой системы
		self.file_model = QFileSystemModel()
		self.file_model.setRootPath(self.root_path)
		self.file_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

		# Прокси-модель для фильтрации
		self.proxy_model = QSortFilterProxyModel()
		self.proxy_model.setSourceModel(self.file_model)
		self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
		# ВАЖНО: фильтрация будет работать по данным из sourceModel, но нам нужно
		# передавать в фильтр не только текст, но и статус привязки.
		# Для этого переопределим filterAcceptsRow в подклассе.

		# Создадим свой прокси-класс
		class FileFilterProxyModel(QSortFilterProxyModel):
			def __init__(self, parent=None):
				super().__init__(parent)
				self.show_mode = "all"
				self.linked_paths = set()
				self.root_path = ""

			def set_show_mode(self, mode):
				self.show_mode = mode
				self.invalidateFilter()

			def set_linked_paths(self, paths):
				self.linked_paths = paths
				self.invalidateFilter()

			def set_root_path(self, path):
				self.root_path = path

			def filterAcceptsRow(self, source_row, source_parent):
				# Получаем путь к файлу из source-модели
				source_model = self.sourceModel()
				index = source_model.index(source_row, 0, source_parent)
				file_path = source_model.filePath(index)
				relative_path = os.path.relpath(file_path, self.root_path).replace("\\", "/")

				# Проверяем, привязан ли файл
				is_linked = relative_path in self.linked_paths

				# Режим отображения
				if self.show_mode == "all":
					return True
				elif self.show_mode == "unlinked":
					return not is_linked
				elif self.show_mode == "linked":
					return is_linked
				return True
				
		self.proxy_model = FileFilterProxyModel()
		self.proxy_model.setSourceModel(self.file_model)
		self.proxy_model.set_root_path(self.root_path)
		self.proxy_model.set_linked_paths(self.get_all_linked_paths())

		self.file_tree = QTreeView()
		self.file_tree.setModel(self.proxy_model)
		self.file_tree.setRootIndex(self.proxy_model.mapFromSource(self.file_model.index(self.root_path)))

		splitter.addWidget(left_panel)

		# Правая панель: вкладки
		right_panel = QTabWidget()
		splitter.addWidget(right_panel)

		# Вкладка проектов
		self.projects_widget = self.create_category_tab("PROJECTS")
		right_panel.addTab(self.projects_widget, "Проекты")

		# Вкладка субъектов
		self.subjects_widget = self.create_category_tab("SUBJECTS")
		right_panel.addTab(self.subjects_widget, "Субъекты")

		splitter.setSizes([600, 600])

	def create_category_tab(self, category_type):
		"""Создаёт вкладку с категориями и файлами"""
		widget = QWidget()
		layout = QHBoxLayout(widget)

		splitter = QSplitter(Qt.Orientation.Horizontal)
		layout.addWidget(splitter)

		# Левая колонка: список категорий
		left_col = QWidget()
		left_layout = QVBoxLayout(left_col)
		left_layout.setContentsMargins(0, 0, 0, 0)

		btn_layout = QHBoxLayout()
		btn_add = QPushButton("➕ Добавить")
		btn_add.clicked.connect(lambda: self.add_category(category_type))
		btn_delete = QPushButton("➖ Удалить")
		btn_delete.clicked.connect(lambda: self.delete_category(category_type))
		btn_layout.addWidget(btn_add)
		btn_layout.addWidget(btn_delete)
		left_layout.addLayout(btn_layout)

		cat_list = CategoryListWidget(category_type, self)
		self.category_lists[category_type] = cat_list
		self.populate_category_list(category_type, cat_list)
		left_layout.addWidget(cat_list)

		splitter.addWidget(left_col)

		# Правая колонка: файлы выбранной категории
		right_col = QWidget()
		right_layout = QVBoxLayout(right_col)
		right_layout.setContentsMargins(0, 0, 0, 0)

		label = QLabel("Файлы в категории:")
		right_layout.addWidget(label)

		file_list = FileListWidget()
		file_list.main_window = self
		file_list.category_type = category_type
		self.category_file_lists[category_type] = file_list
		right_layout.addWidget(file_list)

		splitter.addWidget(right_col)
		splitter.setSizes([250, 350])

		return widget

	def populate_category_list(self, category_type, list_widget):
		list_widget.clear()
		for cat_name in self.index_data[category_type].keys():
			list_widget.addItem(cat_name)

	def add_category(self, category_type):
		name, ok = QInputDialog.getText(self, "Новая категория", "Введите название:")
		if ok and name.strip():
			name = name.strip()
			if name not in self.index_data[category_type]:
				self.index_data[category_type][name] = []
				self.populate_category_list(category_type, self.category_lists[category_type])
				self.save_index()
			else:
				QMessageBox.warning(self, "Ошибка", "Категория с таким именем уже существует.")

	def delete_category(self, category_type):
		list_widget = self.category_lists[category_type]
		current = list_widget.currentItem()
		if current:
			name = current.text()
			reply = QMessageBox.question(
				self, "Подтверждение",
				f"Удалить категорию '{name}'? Это действие необратимо.",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
			)
			if reply == QMessageBox.StandardButton.Yes:
				del self.index_data[category_type][name]
				self.populate_category_list(category_type, list_widget)
				self.category_file_lists[category_type].clear()
				self.save_index()

	def show_category_files(self, category_type, category_name):
		file_list = self.category_file_lists.get(category_type)
		if file_list is None:
			return
		file_list.clear()
		file_list.category_type = category_type
		file_list.category_name = category_name
		files = self.index_data[category_type].get(category_name, [])
		for f in files:
			file_list.addItem(f)

	def show_file_context_menu(self, position):
		index = self.file_tree.indexAt(position)
		if not index.isValid():
			return

		path = self.file_model.filePath(index)
		relative_path = os.path.relpath(path, self.root_path).replace("\\", "/")

		menu = QMenu()
		# Привязка к проекту
		projects_menu = QMenu("Привязать к проекту", self)
		for proj in self.index_data["PROJECTS"].keys():
			action = QAction(proj, self)
			action.triggered.connect(lambda checked, p=proj: self.assign_file_to_category("PROJECTS", p, relative_path))
			projects_menu.addAction(action)
		menu.addMenu(projects_menu)

		# Привязка к субъекту
		subjects_menu = QMenu("Привязать к субъекту", self)
		for subj in self.index_data["SUBJECTS"].keys():
			action = QAction(subj, self)
			action.triggered.connect(lambda checked, s=subj: self.assign_file_to_category("SUBJECTS", s, relative_path))
			subjects_menu.addAction(action)
		menu.addMenu(subjects_menu)

		menu.exec(self.file_tree.viewport().mapToGlobal(position))

	def assign_file_to_category(self, category_type, category_name, file_path):
		if file_path not in self.index_data[category_type][category_name]:
			self.index_data[category_type][category_name].append(file_path)
			self.save_index()
			# Если эта категория сейчас открыта, обновить список файлов
			file_list = self.category_file_lists.get(category_type)
			if file_list and file_list.category_name == category_name:
				self.show_category_files(category_type, category_name)
			QMessageBox.information(self, "Готово", f"Файл привязан к '{category_name}'")
		else:
			QMessageBox.information(self, "Информация", "Файл уже привязан к этой категории")

	def remove_file_from_category(self, category_type, category_name, file_path):
		if file_path in self.index_data[category_type][category_name]:
			self.index_data[category_type][category_name].remove(file_path)
			self.save_index()
			self.show_category_files(category_type, category_name)

	def filter_files(self, text):
		self.proxy_model.setFilterFixedString(text)
		
	def update_linked_paths(self):
		paths = set()
		for cat_type in ["PROJECTS", "SUBJECTS"]:
			for files in self.index_data[cat_type].values():
				paths.update(files)
		self.proxy_model.set_linked_paths(paths)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = MainWindow(json_path="index.json", root_path="E:/Jericho")
	window.show()
	sys.exit(app.exec())