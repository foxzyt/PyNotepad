# Conteúdo completo para o arquivo: highlighters.py

from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt6.QtCore import QRegularExpression

# --- CLASSES DE HIGHLIGHTER ---
class BaseHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class PythonSyntaxHighlighter(BaseHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        keyword = QTextCharFormat(); keyword.setForeground(QColor("#ff79c6")); keyword.setFontWeight(QFont.Weight.Bold)
        string = QTextCharFormat(); string.setForeground(QColor("#f1fa8c"))
        comment = QTextCharFormat(); comment.setForeground(QColor("#6272a4")); comment.setFontItalic(True)
        number = QTextCharFormat(); number.setForeground(QColor("#bd93f9"))
        decorator = QTextCharFormat(); decorator.setForeground(QColor("#ffb86c"))
        self_keyword = QTextCharFormat(); self_keyword.setForeground(QColor("#9a7ecc")); self_keyword.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\b(def|class|if|elif|else|for|while|try|except|finally|return|yield|import|from|as|pass|continue|break|in|is|not|and|or|with|True|False|None)\b"), keyword))
        self.highlighting_rules.append((QRegularExpression(r"\"\"\".*?\"\"\"", QRegularExpression.PatternOption.DotMatchesEverythingOption), comment))
        self.highlighting_rules.append((QRegularExpression(r"'''.*?'''", QRegularExpression.PatternOption.DotMatchesEverythingOption), comment))
        self.highlighting_rules.append((QRegularExpression(r"\"[^\"]*\""), string))
        self.highlighting_rules.append((QRegularExpression(r"'[^']*'"), string))
        self.highlighting_rules.append((QRegularExpression(r"#[^\n]*"), comment))
        self.highlighting_rules.append((QRegularExpression(r"\b[0-9]+\.?[0-9]*\b"), number))
        self.highlighting_rules.append((QRegularExpression(r"@\w+"), decorator))
        self.highlighting_rules.append((QRegularExpression(r"\bself\b"), self_keyword))

class HtmlSyntaxHighlighter(BaseHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        tag = QTextCharFormat(); tag.setForeground(QColor("#ff79c6"))
        attribute = QTextCharFormat(); attribute.setForeground(QColor("#50fa7b"))
        value = QTextCharFormat(); value.setForeground(QColor("#f1fa8c"))
        comment = QTextCharFormat(); comment.setForeground(QColor("#6272a4")); comment.setFontItalic(True)
        self.highlighting_rules.append((QRegularExpression(r"</?\s*\w+"), tag))
        self.highlighting_rules.append((QRegularExpression(r"\s+\w+\s*="), attribute))
        self.highlighting_rules.append((QRegularExpression(r"(\"[^\"]*\"|'[^']*')"), value))
        self.highlighting_rules.append((QRegularExpression(r"", QRegularExpression.PatternOption.DotMatchesEverythingOption), comment))

class CssSyntaxHighlighter(BaseHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        selector = QTextCharFormat(); selector.setForeground(QColor("#50fa7b")); selector.setFontWeight(QFont.Weight.Bold)
        property_format = QTextCharFormat(); property_format.setForeground(QColor("#8be9fd"))
        comment = QTextCharFormat(); comment.setForeground(QColor("#6272a4")); comment.setFontItalic(True)
        self.highlighting_rules.append((QRegularExpression(r"(^|^\s*)[^\{\}]+(?=\s*\{)"), selector))
        self.highlighting_rules.append((QRegularExpression(r"([a-zA-Z-]+)(?=\s*:)"), property_format))
        self.highlighting_rules.append((QRegularExpression(r"/\*.*?\*/", QRegularExpression.PatternOption.DotMatchesEverythingOption), comment))

class JavaScriptSyntaxHighlighter(BaseHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        keyword = QTextCharFormat(); keyword.setForeground(QColor("#ff79c6")); keyword.setFontWeight(QFont.Weight.Bold)
        string = QTextCharFormat(); string.setForeground(QColor("#f1fa8c"))
        comment = QTextCharFormat(); comment.setForeground(QColor("#6272a4")); comment.setFontItalic(True)
        number = QTextCharFormat(); number.setForeground(QColor("#bd93f9"))
        function = QTextCharFormat(); function.setForeground(QColor("#50fa7b"))
        keywords = ["\\b(const|let|var|if|else|for|while|return|function|import|export|from|new|this|class|extends|super|async|await|try|catch)\\b"]
        self.highlighting_rules.append((QRegularExpression(keywords[0]), keyword))
        self.highlighting_rules.append((QRegularExpression(r"`[^`]*`"), string))
        self.highlighting_rules.append((QRegularExpression(r"\"[^\"]*\""), string))
        self.highlighting_rules.append((QRegularExpression(r"'[^']*'"), string))
        self.highlighting_rules.append((QRegularExpression(r"//[^\n]*"), comment))
        self.highlighting_rules.append((QRegularExpression(r"/\*.*?\*/", QRegularExpression.PatternOption.DotMatchesEverythingOption), comment))
        self.highlighting_rules.append((QRegularExpression(r"\b[0-9]+\.?[0-9]*\b"), number))
        self.highlighting_rules.append((QRegularExpression(r"\b\w+(?=\s*\()"), function))

class JsonSyntaxHighlighter(BaseHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        key = QTextCharFormat(); key.setForeground(QColor("#8be9fd"))
        string = QTextCharFormat(); string.setForeground(QColor("#f1fa8c"))
        number = QTextCharFormat(); number.setForeground(QColor("#bd93f9"))
        boolean = QTextCharFormat(); boolean.setForeground(QColor("#ff79c6")); boolean.setFontWeight(QFont.Weight.Bold)
        null = QTextCharFormat(); null.setForeground(QColor("#ff79c6")); null.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((QRegularExpression(r"\"(\\s|[^\"\\])*\"(?=\s*:)"), key))
        self.highlighting_rules.append((QRegularExpression(r"\"(\\s|[^\"\\])*\"(?!(\s*:))"), string))
        self.highlighting_rules.append((QRegularExpression(r"\b[0-9]+\.?[0-9]*\b"), number))
        self.highlighting_rules.append((QRegularExpression(r"\b(true|false)\b"), boolean))
        self.highlighting_rules.append((QRegularExpression(r"\bnull\b"), null))