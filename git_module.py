# git_module.py
import os
import subprocess

class GitModule:
    """
    Uma classe para interagir com o Git a partir de um diretório de repositório.
    """
    def __init__(self, repo_path=None):
        self.repo_path = repo_path

    def set_repo_path(self, repo_path):
        """Define o caminho do repositório a ser usado para os comandos."""
        self.repo_path = repo_path

    def _execute_command(self, command):
        """
        Executa um comando Git no shell e retorna a saída.

        Args:
            command (list): A lista de argumentos do comando (ex: ['status', '--porcelain']).

        Returns:
            tuple: Uma tupla contendo (stdout, stderr, return_code).
                   Retorna (None, "Git não encontrado...", -1) se o Git não estiver instalado.
                   Retorna (None, "Caminho do repositório não definido", -1) se o caminho não for setado.
        """
        if not self.repo_path or not os.path.isdir(self.repo_path):
            return None, "O caminho do repositório não é um diretório válido.", -1

        try:
            # Usar startupinfo para evitar que a janela do console apareça no Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                ['git'] + command,
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                startupinfo=startupinfo
            )
            stdout, stderr = process.communicate()
            return stdout.strip(), stderr.strip(), process.returncode
        except FileNotFoundError:
            return None, "Comando 'git' não encontrado. Verifique se o Git está instalado e no PATH do sistema.", -1
        except Exception as e:
            return None, f"Ocorreu um erro inesperado: {e}", -1

    def status(self):
        """Executa 'git status' e retorna a saída."""
        return self._execute_command(['status'])

    def add(self, file_path='.'):
        """Adiciona arquivos ao stage. Por padrão, adiciona tudo."""
        return self._execute_command(['add', file_path])

    def commit(self, message):
        """Executa 'git commit' com uma mensagem."""
        if not message:
            return None, "A mensagem de commit não pode ser vazia.", 1
        return self._execute_command(['commit', '-m', message])

    def push(self, remote='origin', branch='master'):
        """Executa 'git push' para um repositório remoto."""
        return self._execute_command(['push', remote, branch])

    def pull(self, remote='origin', branch='master'):
        """Executa 'git pull' de um repositório remoto."""
        return self._execute_command(['pull', remote, branch])

    def init(self):
        """Inicializa um novo repositório com 'git init'."""
        return self._execute_command(['init'])