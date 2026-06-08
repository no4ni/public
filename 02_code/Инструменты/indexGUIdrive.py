import sys
import json
import os
from PyQt6.QtCore import QSortFilterProxyModel
from PyQt6.QtWidgets import (
	QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
	QTreeView, QListWidget, QPushButton, QInputDialog,
	QMessageBox, QMenu, QTabWidget, QSplitter, QAbstractItemView,
	QLabel, QLineEdit, QStatusBar, QComboBox
)
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QFileSystemModel, QAction

class FileFilterProxyModel(QSortFilterProxyModel):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.indexed_folders = set()
		self.root_path = ""
		self.filter_text = ""
		self.filter_mode = "unlinked"  # "unlinked", "all", "linked"

	def set_indexed_folders(self, folders):
		self.indexed_folders = folders
		self.invalidateFilter()

	def set_root_path(self, path):
		self.root_path = os.path.normpath(path)

	def set_filter_text(self, text):
		self.filter_text = text.lower()
		self.invalidateFilter()

	def set_filter_mode(self, mode):
		self.filter_mode = mode
		self.invalidateFilter()

	def filterAcceptsRow(self, source_row, source_parent):
		source_model = self.sourceModel()
		if not source_model:
			return False
		index = source_model.index(source_row, 0, source_parent)
		if source_model.isDir(index):
			return True
		file_path = source_model.filePath(index)
		norm_path = os.path.normpath(file_path)
		if not norm_path.startswith(self.root_path):
			return False
		relative_path = os.path.relpath(norm_path, self.root_path).replace("\\", "/")
		file_folder = os.path.dirname(relative_path)
		is_linked = file_folder in self.indexed_folders

		if self.filter_mode == "unlinked" and is_linked:
			return False
		if self.filter_mode == "linked" and not is_linked:
			return False
		if self.filter_text and self.filter_text not in file_path.lower():
			return False
		return True


class CategoryListWidget(QListWidget):
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
			self.main_window.remove_file_from_category(
				self.category_type, self.category_name, current.text()
			)


class MainWindow(QMainWindow):
	def __init__(self, json_path="index.json", root_path="E:/Jericho"):
		super().__init__()
		self.json_path = json_path
		self.root_path = root_path
		self.index_data = self.load_index()
		self.category_lists = {}
		self.category_file_lists = {}
		self.initUI()
		self.check_root_path()

	def load_index(self):
		if os.path.exists(self.json_path):
			with open(self.json_path, 'r', encoding='utf-8') as f:
				raw_data = json.load(f)
				normalized = {}
				for cat_type, categories in raw_data.items():
					clean_type = cat_type.strip()
					normalized[clean_type] = {}
					for cat_name, files in categories.items():
						clean_name = cat_name.strip()
						normalized[clean_type][clean_name] = [f.strip() for f in files]
				return normalized
		return {"PROJECTS": {}, "SUBJECTS": {}}

	def save_index(self):
		with open(self.json_path, 'w', encoding='utf-8') as f:
			json.dump(self.index_data, f, ensure_ascii=False, indent=2)

	def check_root_path(self):
		if not os.path.exists(self.root_path):
			QMessageBox.critical(self, "Ошибка", f"Папка не найдена: {self.root_path}")
			return
		root_files = [f for f in os.listdir(self.root_path)
					  if os.path.isfile(os.path.join(self.root_path, f))]
		indexed_folders = self.get_indexed_folders()
		self.statusBar.showMessage(
			f"Файлов в корне: {len(root_files)} | Индексировано папок: {len(indexed_folders)}",
			10000
		)

	def get_indexed_folders(self):
		folders = set()
		for cat_type in ["PROJECTS", "SUBJECTS"]:
			if cat_type not in self.index_data:
				continue
			for files in self.index_data[cat_type].values():
				for item_path in files:
					item_path = item_path.strip()
					if not item_path:
						continue
					full_path = os.path.join(self.root_path, item_path)
					if os.path.isdir(full_path):
						folders.add(item_path.replace("\\", "/"))
						for root, dirs, _ in os.walk(full_path):
							for d in dirs:
								subfolder = os.path.relpath(
									os.path.join(root, d), self.root_path
								).replace("\\", "/")
								folders.add(subfolder)
					else:
						folder = os.path.dirname(item_path.replace("\\", "/"))
						if folder:
							folders.add(folder)
		return folders

	def update_indexed_folders(self):
		folders = self.get_indexed_folders()
		self.proxy_model.set_indexed_folders(folders)
		self.statusBar.showMessage(f"Индексировано папок: {len(folders)}", 5000)

	def initUI(self):
		self.setWindowTitle("Иерихон: редактор связей файлов")
		self.setGeometry(100, 100, 1200, 700)
		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)

		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		main_layout = QHBoxLayout(central_widget)

		splitter = QSplitter(Qt.Orientation.Horizontal)
		main_layout.addWidget(splitter)

		# Левая панель: дерево файлов
		left_panel = QWidget()
		left_layout = QVBoxLayout(left_panel)
		left_layout.setContentsMargins(0, 0, 0, 0)

		filter_layout = QHBoxLayout()
		self.filter_combo = QComboBox()
		self.filter_combo.addItems(["Неиндексированные", "Все файлы", "Только индексированные"])
		self.filter_combo.currentTextChanged.connect(self.change_filter_mode)
		filter_layout.addWidget(QLabel("Режим:"))
		filter_layout.addWidget(self.filter_combo)
		left_layout.addLayout(filter_layout)

		self.search_edit = QLineEdit()
		self.search_edit.setPlaceholderText("Поиск файлов...")
		self.search_edit.textChanged.connect(self.filter_files)
		left_layout.addWidget(self.search_edit)

		self.file_model = QFileSystemModel()
		self.file_model.setRootPath(self.root_path)
		self.file_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

		self.proxy_model = FileFilterProxyModel()
		self.proxy_model.setSourceModel(self.file_model)
		self.proxy_model.set_root_path(self.root_path)
		self.update_indexed_folders()

		self.file_tree = QTreeView()
		self.file_tree.setModel(self.proxy_model)
		root_index = self.file_model.index(self.root_path)
		mapped_root = self.proxy_model.mapFromSource(root_index)
		self.file_tree.setRootIndex(mapped_root)
		self.file_tree.setExpanded(mapped_root, True)
		self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.file_tree.customContextMenuRequested.connect(self.show_file_context_menu)
		self.file_tree.setAnimated(False)
		self.file_tree.setIndentation(20)
		self.file_tree.setSortingEnabled(True)
		left_layout.addWidget(self.file_tree)

		splitter.addWidget(left_panel)

		# Правая панель: вкладки
		right_panel = QTabWidget()
		splitter.addWidget(right_panel)

		self.projects_widget = self.create_category_tab("PROJECTS")
		right_panel.addTab(self.projects_widget, "Проекты")

		self.subjects_widget = self.create_category_tab("SUBJECTS")
		right_panel.addTab(self.subjects_widget, "Субъекты")

		splitter.setSizes([600, 600])

	def change_filter_mode(self, mode):
		mode_map = {
			"Неиндексированные": "unlinked",
			"Все файлы": "all",
			"Только индексированные": "linked"
		}
		self.proxy_model.set_filter_mode(mode_map.get(mode, "unlinked"))

	def filter_files(self, text):
		self.proxy_model.set_filter_text(text)

	def transfer_category(self, source_type, target_type):
		"""Переносит выделенную категорию из source_type в target_type."""
		list_widget = self.category_lists.get(source_type)
		if not list_widget:
			return
		current_item = list_widget.currentItem()
		if not current_item:
			QMessageBox.warning(self, "Ошибка", "Выберите категорию для переноса.")
			return

		category_name = current_item.text()

		# 1. Забираем файлы из исходной категории
		files = self.index_data[source_type].get(category_name, [])

		# 2. Удаляем категорию из исходного типа
		del self.index_data[source_type][category_name]

		# 3. Добавляем (или заменяем) в целевом типе
		self.index_data[target_type][category_name] = files

		# 4. Сохраняем индекс
		self.save_index()

		# 5. Обновляем списки категорий в обеих вкладках
		self.populate_category_list(source_type, self.category_lists[source_type])
		self.populate_category_list(target_type, self.category_lists[target_type])

		# 6. Очищаем отображение файлов (категория пропала из исходной вкладки)
		file_list = self.category_file_lists.get(source_type)
		if file_list:
			file_list.clear()

		# 7. Обновляем индексацию папок (если у тебя это влияет на дерево)
		self.update_indexed_folders()

		# 8. Сообщаем в статусную строку
		self.statusBar.showMessage(f"Категория '{category_name}' перенесена из {source_type} в {target_type}.", 5000)

	def create_category_tab(self, category_type):
		widget = QWidget()
		layout = QHBoxLayout(widget)
		splitter = QSplitter(Qt.Orientation.Horizontal)
		layout.addWidget(splitter)

		# Левая колонка: список категорий
		left_col = QWidget()
		left_layout = QVBoxLayout(left_col)
		btn_layout = QHBoxLayout()
		btn_add = QPushButton("➕ Добавить")
		btn_add.clicked.connect(lambda: self.add_category(category_type))
		btn_delete = QPushButton("➖ Удалить")
		btn_delete.clicked.connect(lambda: self.delete_category(category_type))
		btn_layout.addWidget(btn_add)
		btn_layout.addWidget(btn_delete)
		left_layout.addLayout(btn_layout)
		btn_layout.addWidget(btn_delete)
		# НОВАЯ КНОПКА ПЕРЕНОСА
		btn_transfer = QPushButton("↔ Перенести в Проекты" if category_type == "SUBJECTS" else "↔ Перенести в Субъекты")
		# Определяем целевой тип для переноса
		target_type = "PROJECTS" if category_type == "SUBJECTS" else "SUBJECTS"
		btn_transfer.clicked.connect(lambda _, st=category_type, tt=target_type: self.transfer_category(st, tt))
		btn_layout.addWidget(btn_transfer)

		left_layout.addLayout(btn_layout)

		cat_list = CategoryListWidget(category_type, self)
		self.category_lists[category_type] = cat_list
		self.populate_category_list(category_type, cat_list)
		left_layout.addWidget(cat_list)
		splitter.addWidget(left_col)

		# Правая колонка: файлы категории
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
				f"Удалить категорию '{name}'?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
			)
			if reply == QMessageBox.StandardButton.Yes:
				del self.index_data[category_type][name]
				self.populate_category_list(category_type, list_widget)
				self.category_file_lists[category_type].clear()
				self.update_indexed_folders()
				self.save_index()

	def show_category_files(self, category_type, category_name):
		file_list = self.category_file_lists.get(category_type)
		if file_list is None:
			return
		file_list.clear()
		file_list.category_name = category_name
		files = self.index_data[category_type].get(category_name, [])
		for f in files:
			file_list.addItem(f)

	def show_file_context_menu(self, position):
		proxy_index = self.file_tree.indexAt(position)
		if not proxy_index.isValid():
			return
		source_index = self.proxy_model.mapToSource(proxy_index)
		if self.file_model.isDir(source_index):
			return
		path = self.file_model.filePath(source_index)
		if not path:
			return
		relative_path = os.path.relpath(path, self.root_path).replace("\\", "/")

		menu = QMenu(self)
		if "PROJECTS" in self.index_data:
			proj_menu = menu.addMenu("Привязать к проекту")
			for proj in self.index_data["PROJECTS"]:
				act = QAction(proj, self)
				act.triggered.connect(lambda _, p=proj: self.assign_file_to_category("PROJECTS", p, relative_path))
				proj_menu.addAction(act)
		if "SUBJECTS" in self.index_data:
			subj_menu = menu.addMenu("Привязать к субъекту")
			for subj in self.index_data["SUBJECTS"]:
				act = QAction(subj, self)
				act.triggered.connect(lambda _, s=subj: self.assign_file_to_category("SUBJECTS", s, relative_path))
				subj_menu.addAction(act)
		menu.exec(self.file_tree.viewport().mapToGlobal(position))

	def assign_file_to_category(self, category_type, category_name, file_path):
		if file_path not in self.index_data[category_type][category_name]:
			self.index_data[category_type][category_name].append(file_path)
			self.save_index()
			self.update_indexed_folders()
			file_list = self.category_file_lists.get(category_type)
			if file_list and file_list.category_name == category_name:
				self.show_category_files(category_type, category_name)
			QMessageBox.information(self, "Готово", f"Файл привязан к '{category_name}'")
		else:
			QMessageBox.information(self, "Информация", "Файл уже привязан")

	def remove_file_from_category(self, category_type, category_name, file_path):
		if (category_type in self.index_data and
			category_name in self.index_data[category_type] and
			file_path in self.index_data[category_type][category_name]):
			self.index_data[category_type][category_name].remove(file_path)
			self.save_index()
			self.update_indexed_folders()
			self.show_category_files(category_type, category_name)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = MainWindow(json_path="index.json", root_path="E:/Jericho")
	window.show()
	sys.exit(app.exec())