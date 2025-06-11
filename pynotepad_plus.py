import sys
import os
import subprocess
import re
import urllib.parse
from webbrowser import open as open_browser

# Imports dos nossos novos módulos
from highlighters import PythonSyntaxHighlighter, HtmlSyntaxHighlighter, CssSyntaxHighlighter, \
    JavaScriptSyntaxHighlighter, JsonSyntaxHighlighter
from terminal import InteractiveTerminal
from git_module import GitModule

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QTextEdit, QFileDialog, QMessageBox,
    QWidget, QStatusBar, QTabWidget, QLabel, QDialog, QLineEdit,
    QPushButton, QHBoxLayout, QFormLayout, QCheckBox, QDockWidget, QFontDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QVBoxLayout, QComboBox, QToolBar, QInputDialog
)
from PyQt6.QtGui import (
    QAction, QFont, QTextCharFormat, QColor, QKeySequence,
    QPainter, QTextDocument
)
from PyQt6.QtCore import Qt, QRegularExpression, QSize, pyqtSignal, QSettings, QTranslator, QCoreApplication, QEvent

import qtawesome as qta

# Definindo o caminho raiz do aplicativo
APP_ROOT = os.path.dirname(os.path.abspath(__file__))


# --- WIDGETS PERSONALIZADOS ---
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    positionChanged = pyqtSignal(int, int)

    def __init__(self, parent=None, font=None):
        super().__init__(parent)
        if font:
            self.setFont(font)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.on_cursor_position_changed)
        self.update_line_number_area_width(0)
        self.on_cursor_position_changed()

    def on_cursor_position_changed(self):
        self.highlight_current_line()
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        self.positionChanged.emit(line, col)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#6272a4"))
                painter.drawText(0, int(top), self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(cr.left(), cr.top(), self.line_number_area_width(), cr.height())

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def line_number_area_width(self):
        digits = 1
        if self.blockCount() > 0:
            digits = len(str(self.blockCount()))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            current_line = cursor.block().text()
            indentation = re.match(r"^\s*", current_line).group(0)
            if current_line.strip().endswith(':'):
                indentation += '    '
            super().keyPressEvent(event)
            self.textCursor().insertText(indentation)
        else:
            super().keyPressEvent(event)


class FindDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.find_field = QLineEdit(self)
        self.replace_field = QLineEdit(self)
        self.case_sensitive_checkbox = QCheckBox()
        self.find_next_button = QPushButton()
        self.replace_button = QPushButton()
        self.replace_all_button = QPushButton()
        layout = QFormLayout(self)
        self.find_label = QLabel()
        self.replace_label = QLabel()
        layout.addRow(self.find_label, self.find_field)
        layout.addRow(self.replace_label, self.replace_field)
        layout.addWidget(self.case_sensitive_checkbox)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.find_next_button)
        button_layout.addWidget(self.replace_button)
        button_layout.addWidget(self.replace_all_button)
        layout.addRow(button_layout)
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("Localizar e Substituir"))
        self.find_label.setText(self.tr("Localizar:"))
        self.replace_label.setText(self.tr("Substituir por:"))
        self.case_sensitive_checkbox.setText(self.tr("Diferenciar maiúsculas/minúsculas"))
        self.find_next_button.setText(self.tr("Localizar Próximo"))
        self.replace_button.setText(self.tr("Substituir"))
        self.replace_all_button.setText(self.tr("Substituir Tudo"))


class ShortcutEditorDialog(QDialog):
    def __init__(self, actions_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Editor de Atalhos"))
        self.setMinimumSize(400, 500)
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([self.tr("Ação"), self.tr("Atalho")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        QMessageBox.information(self, self.tr("Em desenvolvimento"),
                                self.tr("O editor de atalhos ainda está em desenvolvimento."))
        layout.addWidget(self.table)


# --- CLASSE PRINCIPAL DA APLICAÇÃO ---
class PyNotepadPlusPlus(QMainWindow):
    def __init__(self):
        super().__init__()
        self.translator = QTranslator(self)
        self.find_dialog = FindDialog(self)
        self.current_font = QFont("Consolas", 12)
        self.git = GitModule()

        self.define_themes()
        self.init_ui()
        self.load_settings()

    def event(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        return super().event(event)

    def init_ui(self):
        self.setGeometry(100, 100, 1200, 800)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_status_on_tab_change)
        self.setCentralWidget(self.tabs)

        self.terminal_dock = QDockWidget(self.tr("Terminal Interativo"))
        self.terminal = InteractiveTerminal(self)
        self.terminal_dock.setWidget(self.terminal)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.terminal_dock)
        self.terminal_dock.hide()

        self.main_toolbar = QToolBar(self.tr("Ferramentas Principais"))
        self.addToolBar(self.main_toolbar)

        lang_toolbar = QToolBar(self.tr("Idioma"))
        self.addToolBar(lang_toolbar)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Português", "pt")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Español", "es")
        self.lang_combo.currentTextChanged.connect(self.on_lang_changed)
        lang_toolbar.addWidget(self.lang_combo)

        self.create_actions()
        self.create_menus()
        self.create_status_bar()

        self.find_dialog.find_next_button.clicked.connect(self.find_text)
        self.find_dialog.replace_button.clicked.connect(self.replace_text)
        self.find_dialog.replace_all_button.clicked.connect(self.replace_all_text)

        self.retranslate_ui()

    def create_actions(self):
        # Ações de Arquivo
        self.action_new = QAction(self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self.new_file)

        self.action_open = QAction(self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self.open_file)

        self.action_save = QAction(self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self.save_current_tab)

        self.action_save_as = QAction(self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.triggered.connect(self.save_file_as)

        self.action_exit = QAction(self)
        self.action_exit.triggered.connect(self.close)

        # Ações de Edição
        self.action_find = QAction(self)
        self.action_find.setShortcut(QKeySequence.StandardKey.Find)
        self.action_find.triggered.connect(self.find_dialog.show)

        self.action_search_web = QAction(self)
        self.action_search_web.setShortcut(QKeySequence("Ctrl+E"))
        self.action_search_web.triggered.connect(self.search_on_web)

        # Ações de Execução
        self.action_run = QAction(self)
        self.action_run.setShortcut(QKeySequence("F5"))
        self.action_run.triggered.connect(self.run_code)

        # Ações de Customização
        self.action_change_font = QAction(self)
        self.action_change_font.triggered.connect(self.change_editor_font)

        self.action_edit_shortcuts = QAction(self)
        self.action_edit_shortcuts.triggered.connect(self.edit_shortcuts)

        # Ações do Git
        self.action_git_status = QAction(self)
        self.action_git_status.triggered.connect(self.git_status)

        self.action_git_add_all = QAction(self)
        self.action_git_add_all.triggered.connect(self.git_add_all)

        self.action_git_commit = QAction(self)
        self.action_git_commit.triggered.connect(self.git_commit)

        # Adicionar ações principais à toolbar
        self.main_toolbar.addAction(self.action_new)
        self.main_toolbar.addAction(self.action_open)
        self.main_toolbar.addAction(self.action_save)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.action_run)

    def create_menus(self):
        self.menu_bar = self.menuBar()

        # Menu Arquivo
        self.file_menu = self.menu_bar.addMenu("")
        self.file_menu.addActions([self.action_new, self.action_open, self.action_save, self.action_save_as])
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.action_exit)

        # Menu Editar
        self.edit_menu = self.menu_bar.addMenu("")
        self.edit_menu.addActions([self.action_find, self.action_search_web])

        # Menu Executar
        self.run_menu = self.menu_bar.addMenu("")
        self.run_menu.addAction(self.action_run)

        # Menu Git
        self.git_menu = self.menu_bar.addMenu("")
        self.git_menu.addAction(self.action_git_status)
        self.git_menu.addSeparator()
        self.git_menu.addAction(self.action_git_add_all)
        self.git_menu.addAction(self.action_git_commit)

        # Menu Customização
        self.custom_menu = self.menu_bar.addMenu("")
        self.themes_menu = self.custom_menu.addMenu("")
        for theme_name in self.themes:
            action = QAction(theme_name, self)
            action.triggered.connect(lambda checked, name=theme_name: self.apply_theme(name))
            self.themes_menu.addAction(action)

        self.custom_menu.addSeparator()
        self.custom_menu.addAction(self.action_change_font)
        self.custom_menu.addAction(self.action_edit_shortcuts)

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.position_label = QLabel()
        self.position_label.setObjectName("PositionStatus")
        self.status_bar.addPermanentWidget(self.position_label)

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("PyNotepad++"))
        # Menus
        self.file_menu.setTitle(self.tr("&Arquivo"))
        self.edit_menu.setTitle(self.tr("&Editar"))
        self.run_menu.setTitle(self.tr("&Executar"))
        self.git_menu.setTitle(self.tr("&Git"))
        self.custom_menu.setTitle(self.tr("&Customização"))
        self.themes_menu.setTitle(self.tr("Temas"))

        # Ações
        self.action_new.setText(self.tr("Novo"))
        self.action_open.setText(self.tr("Abrir..."))
        self.action_save.setText(self.tr("Salvar"))
        self.action_save_as.setText(self.tr("Salvar Como..."))
        self.action_exit.setText(self.tr("Sair"))
        self.action_find.setText(self.tr("Localizar/Substituir..."))
        self.action_search_web.setText(self.tr("Pesquisar na Web"))
        self.action_run.setText(self.tr("Executar"))
        self.action_change_font.setText(self.tr("Alterar Fonte do Editor..."))
        self.action_edit_shortcuts.setText(self.tr("Editar Atalhos..."))

        # Ações Git
        self.action_git_status.setText(self.tr("Status"))
        self.action_git_add_all.setText(self.tr("Adicionar Tudo (Add .)"))
        self.action_git_commit.setText(self.tr("Commit..."))

        # Outros Widgets
        self.terminal_dock.setWindowTitle(self.tr("Terminal Interativo"))
        self.status_bar.showMessage(self.tr("Pronto"), 3000)
        self.find_dialog.retranslate_ui()
        self.main_toolbar.setWindowTitle(self.tr("Ferramentas Principais"))

    def on_lang_changed(self, text):
        lang_code = self.lang_combo.currentData()
        if lang_code:
            self.change_language(lang_code)

    def change_language(self, lang_code):
        app = QCoreApplication.instance()
        if self.translator.isEmpty() is False:
            app.removeTranslator(self.translator)
        translation_file = os.path.join(APP_ROOT, f"pynotepad_{lang_code}.qm")
        if self.translator.load(translation_file):
            app.installTranslator(self.translator)
        else:
            print(f"AVISO: Não foi possível carregar o arquivo para o idioma '{lang_code}'.")
        settings = QSettings("PyNotepad++", "Config")
        settings.setValue("language", lang_code)
        QApplication.instance().postEvent(self, QEvent(QEvent.Type.LanguageChange))

    # --- MÉTODOS DE HANDLER DO GIT (CORRIGIDOS) ---

    def _get_current_repo_path(self):
        """Obtém o diretório do arquivo atualmente aberto."""
        editor = self.get_current_editor()
        if not editor or not editor.property("file_path"):
            self.terminal_dock.show()
            # CORRIGIDO: usa self.terminal.append() e adiciona cor à mensagem de erro
            error_msg = f"<font color='#ff5555'>ERRO: {self.tr('Nenhum arquivo de um repositório está aberto.')}</font>"
            self.terminal.append(error_msg)
            return None

        repo_path = os.path.dirname(editor.property("file_path"))
        return repo_path

    def _execute_git_command(self, command_func, *args):
        """Função auxiliar para executar um comando Git e mostrar a saída no terminal."""
        repo_path = self._get_current_repo_path()
        if not repo_path:
            return

        self.git.set_repo_path(repo_path)
        self.terminal_dock.show()
        if hasattr(self.terminal, 'clear'):  # Verifica se o método clear existe
            self.terminal.clear()

        # CORRIGIDO: usa self.terminal.append() e melhora a formatação
        command_name = " ".join([command_func.__name__] + list(args))
        self.terminal.append(f"<font color='#8be9fd'>$ git {command_name}</font>")

        stdout, stderr, returncode = command_func(*args)

        if returncode == 0:
            output = stdout if stdout else self.tr("Comando executado com sucesso.")
            # Usa a tag <pre> para preservar a formatação da saída do git (espaços, quebras de linha)
            self.terminal.append(f"<pre style='color:#f8f8f2;'>{output}</pre>")
        else:
            # CORRIGIDO: usa self.terminal.append() para a saída de erro
            error_msg = f"<font color='#ff5555'>ERRO (código {returncode}):<br><pre>{stderr}</pre></font>"
            if stdout:
                error_msg += f"<br><font color='#f1fa8c'>{self.tr('Saída Padrão')}:<br><pre>{stdout}</pre></font>"
            self.terminal.append(error_msg)
        self.terminal.append("")  # Adiciona uma linha em branco para separar os comandos

    def git_status(self):
        self._execute_git_command(self.git.status)

    def git_add_all(self):
        self._execute_git_command(self.git.add, '.')

    def git_commit(self):
        repo_path = self._get_current_repo_path()
        if not repo_path:
            return

        commit_message, ok = QInputDialog.getMultiLineText(self, self.tr("Commit"),
                                                           self.tr("Digite a mensagem do commit:"))

        if ok and commit_message:
            # Primeiro, adiciona tudo antes de commitar para garantir que as mudanças sejam incluídas
            self.terminal.append(f"<font color='#8be9fd'>$ git add .</font>")
            self.git.set_repo_path(repo_path)
            _, stderr_add, code_add = self.git.add('.')
            if code_add != 0:
                self.terminal.append(f"<font color='#ff5555'>ERRO no git add:<br><pre>{stderr_add}</pre></font>")
                return

            # Executa o commit
            self._execute_git_command(self.git.commit, commit_message)

    # --- FIM DOS MÉTODOS DO GIT ---

    def update_cursor_position(self, line, col):
        self.position_label.setText(f"{self.tr('Linha')}: {line}, {self.tr('Col')}: {col} ")

    def update_status_on_tab_change(self, index):
        if index != -1:
            editor = self.get_current_editor()
            if editor:
                editor.on_cursor_position_changed()
        else:
            self.position_label.clear()

    def get_current_editor(self):
        return self.tabs.currentWidget()

    def define_themes(self):
        self.themes = {
            "Dracula": """
                QMainWindow, QDialog { background-color: #282a36; } QToolBar { background-color: #282a36; border: none; } QMenuBar { background-color: #282a36; color: #f8f8f2; } QMenuBar::item:selected { background-color: #44475a; } QMenu { background-color: #282a36; color: #f8f8f2; border: 1px solid #44475a;} QMenu::item:selected { background-color: #44475a; } QStatusBar { color: #f8f8f2; } CodeEditor, #OutputConsole, LineNumberArea { background-color: #282a36; color: #f8f8f2; border: none; } QPlainTextEdit, QTextEdit { selection-background-color: #44475a; } QTabWidget::pane { border-top: 1px solid #44475a; } QTabBar::tab { background: #282a36; color: #f8f8f2; padding: 10px; border-top-left-radius: 4px; border-top-right-radius: 4px;} QTabBar::tab:selected { background: #44475a; } QTabBar::tab:hover { background: #6272a4; } #PositionStatus { color: #bd93f9; font-weight: bold; padding-right: 10px; } QDockWidget { color: #f8f8f2; } QDockWidget::title { background: #44475a; padding: 5px; }
            """,
            "Light": """
                QMainWindow, QDialog { background-color: #f0f0f0; } QToolBar { background-color: #f0f0f0; border: none; } QMenuBar { background-color: #f0f0f0; color: #333; } QMenuBar::item:selected { background-color: #dcdcdc; } QMenu { background-color: #f8f8f8; color: #333; border: 1px solid #dcdcdc;} QMenu::item:selected { background-color: #dcdcdc; } QStatusBar { color: #333; } CodeEditor, #OutputConsole, LineNumberArea { background-color: #ffffff; color: #000000; border: none; } QPlainTextEdit, QTextEdit { selection-background-color: #add8e6; } QTabWidget::pane { border-top: 1px solid #dcdcdc; } QTabBar::tab { background: #f0f0f0; color: #333; padding: 10px; border-top-left-radius: 4px; border-top-right-radius: 4px;} QTabBar::tab:selected { background: #ffffff; border-bottom: 2px solid #0078d7; } QTabBar::tab:hover { background: #e6e6e6; } #PositionStatus { color: #0078d7; font-weight: bold; padding-right: 10px; } QDockWidget { color: #333; } QDockWidget::title { background: #dcdcdc; padding: 5px; }
            """
        }

    def apply_theme(self, theme_name):
        self.setProperty("theme_name", theme_name)
        style_sheet = self.themes.get(theme_name, "")
        font_size = f"font-size: {self.current_font.pointSize()}pt;"
        self.setStyleSheet(style_sheet + f" CodeEditor {{ {font_size} }}")
        settings = QSettings("PyNotepad++", "Config")
        settings.setValue("theme", theme_name)
        icon_color = "white" if theme_name == "Dracula" else "black"
        self.action_new.setIcon(qta.icon("fa5s.file", color=icon_color))
        self.action_open.setIcon(qta.icon("fa5s.folder-open", color=icon_color))
        self.action_save.setIcon(qta.icon("fa5s.save", color=icon_color))
        self.action_exit.setIcon(qta.icon("fa5s.times-circle", color=icon_color))
        self.action_find.setIcon(qta.icon("fa5s.search", color=icon_color))
        self.action_search_web.setIcon(qta.icon("fa5s.globe-americas", color=icon_color))
        self.action_run.setIcon(qta.icon("fa5s.play", color="#50fa7b" if theme_name == "Dracula" else "green"))

    def _apply_font_to_all_widgets(self):
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if isinstance(editor, CodeEditor):
                editor.setFont(self.current_font)
        current_theme = self.property("theme_name") or "Dracula"
        self.apply_theme(current_theme)

    def change_editor_font(self):
        ok, font = QFontDialog.getFont(self.current_font, self, self.tr("Escolha a Fonte do Editor"))
        if ok:
            self.current_font = font
            self._apply_font_to_all_widgets()
            settings = QSettings("PyNotepad++", "Config")
            settings.setValue("editor_font", self.current_font.toString())

    def edit_shortcuts(self):
        actions_to_edit = {"Novo Arquivo": self.action_new, "Abrir Arquivo": self.action_open}
        dialog = ShortcutEditorDialog(actions_to_edit, self)
        dialog.exec()

    def search_on_web(self):
        editor = self.get_current_editor()
        if not editor: return
        selected_text = editor.textCursor().selectedText()
        if selected_text:
            query = urllib.parse.quote_plus(selected_text)
            url = f"https://www.google.com/search?q={query}"
            open_browser(url)
        else:
            self.status_bar.showMessage(self.tr("Nenhum texto selecionado para pesquisar."), 3000)

    def new_file(self):
        editor = CodeEditor(font=self.current_font)
        editor.setProperty("file_path", None)
        editor.positionChanged.connect(self.update_cursor_position)
        editor.textChanged.connect(self.mark_as_modified)
        index = self.tabs.addTab(editor, self.tr("Novo Arquivo"))
        self.tabs.setCurrentIndex(index)
        self.mark_as_modified()

    def open_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Abrir Arquivos"), "", self.tr("Todos os Arquivos (*.*)"))
        if paths:
            for path in paths:
                self.open_file_in_tab(path)

    def open_file_in_tab(self, path):
        for i in range(self.tabs.count()):
            if self.tabs.widget(i).property("file_path") == path:
                self.tabs.setCurrentIndex(i)
                return
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erro"), f"{self.tr('Não foi possível abrir')}: {e}")
            return

        editor = CodeEditor(font=self.current_font)
        editor.setPlainText(text)
        editor.setProperty("file_path", path)
        editor.positionChanged.connect(self.update_cursor_position)
        editor.textChanged.connect(self.mark_as_modified)
        self.update_highlighter(editor, path)

        index = self.tabs.addTab(editor, os.path.basename(path))
        self.tabs.setCurrentIndex(index)
        self.tabs.setTabToolTip(index, path)
        editor.document().setModified(False)

    def mark_as_modified(self):
        current_widget = self.get_current_editor()
        if not current_widget:
            return
        index = self.tabs.currentIndex()
        if not self.tabs.tabText(index).endswith('*'):
            self.tabs.setTabText(index, self.tabs.tabText(index) + '*')

    def closeEvent(self, event):
        self.terminal.kill_process()
        self.save_settings()
        can_close = True
        while self.tabs.count() > 0:
            if not self.close_tab(0):
                can_close = False
                break
        if can_close:
            super().closeEvent(event)
        else:
            event.ignore()

    def close_tab(self, index):
        editor = self.tabs.widget(index)
        if not editor:
            return True

        if editor.document().isModified():
            file_name = os.path.basename(editor.property("file_path") or self.tr("Novo Arquivo"))

            reply = QMessageBox.question(self, self.tr('Salvar Alterações?'),
                                         self.tr(
                                             "O arquivo '{0}' foi modificado.\nDeseja salvar as alterações?").format(
                                             file_name),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)

            if reply == QMessageBox.StandardButton.Yes:
                if not self.save_tab(index):
                    return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False

        self.tabs.removeTab(index)
        return True

    def save_current_tab(self):
        if self.tabs.count() == 0:
            return True
        return self.save_tab(self.tabs.currentIndex())

    def save_file_as(self):
        if self.tabs.count() == 0:
            return
        self.save_tab(self.tabs.currentIndex(), force_save_as=True)

    def save_tab(self, index, force_save_as=False):
        editor = self.tabs.widget(index)
        if not editor:
            return False
        path = editor.property("file_path")
        if force_save_as or not path:
            file_filter = f"{self.tr('Todos os Arquivos')} (*);;Python (*.py);;HTML (*.html, *.htm);;CSS (*.css);;JavaScript (*.js);;JSON (*.json)"
            new_path, _ = QFileDialog.getSaveFileName(self, self.tr("Salvar Arquivo Como"), "", file_filter)
            if not new_path:
                return False
            path = new_path
            editor.setProperty("file_path", path)
            self.update_highlighter(editor, path)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
            editor.document().setModified(False)
            self.tabs.setTabText(index, os.path.basename(path))
            self.tabs.setTabToolTip(index, path)
            self.status_bar.showMessage(self.tr("Arquivo salvo: {}").format(path), 3000)
            return True
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erro"), f"{self.tr('Não foi possível salvar o arquivo')}:\n{e}")
            return False

    def update_highlighter(self, editor, file_path=None):
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        highlighter_map = {
            '.py': PythonSyntaxHighlighter, '.html': HtmlSyntaxHighlighter, '.htm': HtmlSyntaxHighlighter,
            '.css': CssSyntaxHighlighter, '.js': JavaScriptSyntaxHighlighter, '.json': JsonSyntaxHighlighter,
        }
        highlighter_class = highlighter_map.get(ext)
        if hasattr(editor, 'highlighter') and editor.highlighter:
            editor.highlighter.setDocument(None)
        if highlighter_class:
            editor.highlighter = highlighter_class(editor.document())
        else:
            editor.highlighter = None

    def find_text(self):
        editor = self.get_current_editor()
        if not editor: return
        query = self.find_dialog.find_field.text()

        flags = QTextDocument.FindFlag()
        if self.find_dialog.case_sensitive_checkbox.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively

        if not editor.find(query, flags):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            editor.setTextCursor(cursor)
            editor.find(query, flags)

    def replace_text(self):
        editor = self.get_current_editor()
        if not editor or not editor.textCursor().hasSelection(): return
        replace_str = self.find_dialog.replace_field.text()
        editor.textCursor().insertText(replace_str)

    def replace_all_text(self):
        editor = self.get_current_editor()
        if not editor: return
        find_str = self.find_dialog.find_field.text()
        replace_str = self.find_dialog.replace_field.text()
        text = editor.toPlainText()

        if self.find_dialog.case_sensitive_checkbox.isChecked():
            text = text.replace(find_str, replace_str)
        else:
            text = re.sub(find_str, replace_str, text, flags=re.IGNORECASE)
        editor.setPlainText(text)

    def run_code(self):
        if not self.save_current_tab():
            return
        editor = self.get_current_editor()
        if not editor:
            return
        file_path = editor.property("file_path")

        self.terminal_dock.show()
        self.terminal.run_code(file_path)

    def load_settings(self):
        settings = QSettings("PyNotepad++", "Config")

        lang_code = settings.value("language", "pt")
        self.change_language(lang_code)
        index = self.lang_combo.findData(lang_code)
        if index != -1:
            self.lang_combo.setCurrentIndex(index)

        theme_name = settings.value("theme", "Dracula")
        self.apply_theme(theme_name)

        font_str = settings.value("editor_font")
        if font_str:
            self.current_font.fromString(font_str)

        self._apply_font_to_all_widgets()

        geometry = settings.value("geometry")
        if geometry: self.restoreGeometry(geometry)

        open_files = settings.value("open_files", [], type=list)
        if open_files:
            for path in open_files:
                if os.path.isfile(path): self.open_file_in_tab(path)

    def save_settings(self):
        settings = QSettings("PyNotepad++", "Config")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("editor_font", self.current_font.toString())
        settings.setValue("theme", self.property("theme_name"))
        settings.setValue("language", self.lang_combo.currentData())

        open_files = [self.tabs.widget(i).property("file_path") for i in range(self.tabs.count()) if
                      self.tabs.widget(i).property("file_path")]
        settings.setValue("open_files", open_files)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = PyNotepadPlusPlus()
    main_win.show()
    sys.exit(app.exec())