# Conteúdo completo para o novo arquivo: terminal.py

import sys
import os
from PyQt6.QtWidgets import QWidget, QTextEdit, QVBoxLayout
from PyQt6.QtGui import QFont, QColor, QTextCursor
from PyQt6.QtCore import QProcess, Qt

class TerminalTextEdit(QTextEdit):
    """Um QTextEdit customizado para simular um terminal interativo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet("background-color: #282a36; color: #f8f8f2;")

    def set_process(self, process):
        self.process = process

    def keyPressEvent(self, event):
        # Se o usuário apertar Enter, não movemos o cursor para a nova linha ainda.
        # Capturamos o texto da linha atual.
        if self.process and (event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            last_line = cursor.selectedText()
            
            # Encontra a posição do último prompt para pegar apenas o que o usuário digitou.
            # Este é um exemplo simples. Um terminal real teria uma lógica mais complexa.
            prompt_pos = last_line.rfind('>') + 1 # Acha o último '>'
            if prompt_pos == 0 and len(last_line) > 0: # Caso simples sem prompt
                 command = last_line + '\n'
            else:
                 command = last_line[prompt_pos:].strip() + '\n'
            
            # Envia o comando para o processo
            self.process.write(command.encode('utf-8', 'ignore'))
            
            # Agora sim, insere a nova linha no editor
            super().keyPressEvent(event)
            return

        # Para qualquer outra tecla, o comportamento é o padrão.
        super().keyPressEvent(event)


class InteractiveTerminal(QWidget):
    """O Widget completo que gerencia a interface do terminal e o processo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.console = TerminalTextEdit(self)
        self.console.set_process(self.process)
        
        layout.addWidget(self.console)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode(errors='ignore')
        self.console.moveCursor(QTextCursor.MoveOperation.End)
        self.console.insertPlainText(data)
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode(errors='ignore')
        self.console.moveCursor(QTextCursor.MoveOperation.End)
        # Formata o erro em vermelho
        self.console.textColor().setNamedColor("#ff5555")
        self.console.insertPlainText(data)
        self.console.textColor().setNamedColor("#f8f8f2") # Volta para a cor padrão
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def process_finished(self):
        self.console.append("\n--- Processo finalizado ---")
        self.process.kill()

    def run_code(self, file_path):
        if not file_path or not file_path.endswith('.py'):
            self.console.clear()
            self.console.setText("AVISO: Salve o arquivo como .py para executá-lo.")
            return

        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()

        self.console.clear()
        self.console.append(f"--- Executando: {os.path.basename(file_path)} ---\n")
        
        self.process.start(sys.executable, ["-u", file_path]) # O argumento "-u" força o output a não ter buffer

    def kill_process(self):
        """Método para ser chamado quando a janela principal fechar."""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()