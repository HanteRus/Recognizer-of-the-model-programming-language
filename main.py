import re
from tabulate import tabulate
from typing import List, Tuple, Dict, Any, Optional

class LexicalAnalyzer:
    def __init__(self):
        self.token_specification = [
            ("COMMENT", r'/\*.*?\*/'),  # Многострочный комментарий
            ("NUMBER", r'\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?'),  # Числа (целые и вещественные)
            ("BIN_NUMBER", r'[01]+[Bb]'),  # Двоичное число
            ("OCT_NUMBER", r'[0-7]+[Oo]'),  # Восьмеричное число
            ("DEC_NUMBER", r'\d+[Dd]?'),  # Десятичное число
            ("HEX_NUMBER", r'[0-9A-Fa-f]+[Hh]'),  # Шестнадцатеричное число
            ("KEYWORD", r'\b(let|if|then|else|for|do|while|loop|input|output)\b'),  # Ключевые слова
            ("IDENTIFIER", r'[A-Za-z_][A-Za-z_0-9]*'),  # Идентификаторы
            ("ASSIGN", r'='),  # Присваивание
            ("REL_OP", r'[<>]=?'),  # Операции отношения
            ("ADD_OP", r'[+\-]|or'),  # Операции сложения
            ("MUL_OP", r'[*/]|and'),  # Операции умножения
            ("UNARY_OP", r'not'),  # Унарная операция
            ("DELIMITER", r'[{}();,]'),  # Разделители
            ("WHITESPACE", r'[ \t]+'),  # Пробелы
            ("NEWLINE", r'\n'),  # Новые строки
        ]
        self.token_regex = '|'.join(f'(?P<{name}>{regex})' for name, regex in self.token_specification)

    def tokenize(self, program: str) -> List[Tuple[str, Any]]:
        """
        Лексический анализ программы
        """
        tokens = []
        errors = []
        for match in re.finditer(self.token_regex, program):
            kind = match.lastgroup
            value = match.group(kind)
            if kind in ("WHITESPACE", "NEWLINE", "COMMENT"):
                continue
            elif kind == "NUMBER":
                value = float(value) if '.' in value or 'E' in value or 'e' in value else int(value)
            tokens.append((kind, value))

        # Проверка на оставшиеся нераспознанные символы
        non_matching = re.finditer(r'[^\s]', program)
        for match in non_matching:
            if not any(re.match(spec[1], match.group(0)) for spec in self.token_specification):
                errors.append(f"Неизвестный символ: {match.group(0)}")

        return tokens, errors


class SyntaxAnalyzer:
    def __init__(self, tokens: List[Tuple[str, Any]]):
        self.tokens = tokens
        self.current_token = 0
        self.symbol_table = {}

    def parse(self) -> Dict[str, Any]:
        """
        Синтаксический анализ программы
        """
        try:
            self.parse_program()
            return {"success": True, "symbol_table": self.symbol_table}
        except SyntaxError as e:
            return {"success": False, "error": str(e)}

    def match(self, expected_type: str) -> Optional[Tuple[str, Any]]:
        if self.current_token < len(self.tokens) and self.tokens[self.current_token][0] == expected_type:
            token = self.tokens[self.current_token]
            self.current_token += 1
            return token
        token_found = self.tokens[self.current_token] if self.current_token < len(self.tokens) else "конец файла"
        raise SyntaxError(f"Ожидался {expected_type}, найдено {token_found}")

    def parse_program(self):
        self.match("DELIMITER")  # {
        while self.current_token < len(self.tokens) and self.tokens[self.current_token][1] != "}":
            if self.tokens[self.current_token][0] == "KEYWORD" and self.tokens[self.current_token][1] == "let":
                self.parse_declaration()
            else:
                self.parse_statement()
        self.match("DELIMITER")  # }

    def parse_declaration(self):
        """
        Разбор объявления переменной (let x = 10;)
        """
        self.match("KEYWORD")  # let
        identifier = self.match("IDENTIFIER")  # Переменная
        self.match("ASSIGN")  # Знак =
        value = self.parse_expression()  # Получаем значение
        self.match("DELIMITER")  # ;
        self.symbol_table[identifier[1]] = {"type": "variable", "value": value}
        # Добавляем переменную в множество объявленных
        self.symbol_table[identifier[1]]["declared"] = True

    def parse_statement(self):
        if self.current_token >= len(self.tokens):
            raise SyntaxError("Неожиданный конец файла")

        current = self.tokens[self.current_token]
        if current[0] == "IDENTIFIER" and self.tokens[self.current_token + 1][0] == "ASSIGN":
            self.parse_assignment()
        elif current[0] == "KEYWORD":
            if current[1] == "if":
                self.parse_conditional()
            elif current[1] == "for":
                self.parse_fixed_loop()
            elif current[1] == "do":
                self.parse_while_loop()
            elif current[1] == "input":
                self.parse_input()
            elif current[1] == "output":
                self.parse_output()
        elif current[0] == "DELIMITER" and current[1] == "{":
            self.parse_compound_statement()
        else:
            raise SyntaxError(f"Неизвестный оператор: {current}")

    def parse_conditional(self):
        self.match("KEYWORD")  # if
        condition = self.parse_expression()  # Разбираем условие
        self.match("KEYWORD")  # then
        self.parse_compound_statement()  # Разбираем блок then
        if self.current_token < len(self.tokens) and self.tokens[self.current_token][1] == "else":
            self.match("KEYWORD")  # else
            self.parse_compound_statement()  # Разбираем блок else

    def parse_fixed_loop(self):
        self.match("KEYWORD")  # for
        self.match("IDENTIFIER")
        self.match("ASSIGN")
        self.parse_expression()
        self.match("KEYWORD")  # to/downto (упрощено)
        self.parse_expression()
        self.parse_compound_statement()

    def parse_while_loop(self):
        self.match("KEYWORD")  # do
        self.parse_compound_statement()
        self.match("KEYWORD")  # while
        self.parse_expression()

    def parse_input(self):
        self.match("KEYWORD")  # input
        self.match("IDENTIFIER")
        self.match("DELIMITER")  # ;

    def parse_output(self):
        self.match("KEYWORD")  # output
        self.parse_expression()
        self.match("DELIMITER")  # ;

    def parse_compound_statement(self):
        self.match("DELIMITER")  # {
        while self.current_token < len(self.tokens) and self.tokens[self.current_token][1] != "}":
            self.parse_statement()
        self.match("DELIMITER")  # }

    def parse_assignment(self):
        identifier = self.match("IDENTIFIER")
        self.match("ASSIGN")
        value = self.parse_expression()
        self.match("DELIMITER")  # ;
        if identifier[1] in self.symbol_table:
            self.symbol_table[identifier[1]]["value"] = value
        else:
            self.symbol_table[identifier[1]] = {"type": "variable", "value": value}

    def parse_expression(self) -> Any:
        """
        Разбирает выражения, включая числа, идентификаторы и бинарные операции
        """
        token = self.tokens[self.current_token]
        if token[0] in ("IDENTIFIER", "NUMBER"):
            left = self.match(token[0])  # Либо IDENTIFIER, либо NUMBER
        else:
            raise SyntaxError(f"Ожидался IDENTIFIER или NUMBER, найдено {token}")

        if self.current_token < len(self.tokens) and self.tokens[self.current_token][0] == "REL_OP":
            operator = self.match("REL_OP")
            right = self.parse_expression()  # Рекурсивно разбираем правую часть выражения
            return {"left": left[1], "operator": operator[1], "right": right}

        return left[1]


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = {}
        self.errors = []
        self.declared_variables = set()  # Множество для отслеживания объявленных переменных
        self.undeclared_usage = set()  # Множество для отслеживания использования переменных до их объявления

    def analyze(self, lexical_errors: List[str], parse_result: Dict[str, Any], tokens: List[Tuple[str, Any]]) -> Dict[str, Any]:
        """
        Семантический анализ программы
        """
        # 1. Лексические ошибки - просто копируем
        for lexical_error in lexical_errors:
            self.errors.append(f"Лексическая ошибка: {lexical_error}")

        # 2. Проверка синтаксического анализа - только если он успешен
        if not parse_result["success"]:
            self.errors.append(f"Синтаксическая ошибка: {parse_result['error']}")
            return {"success": False, "errors": self.errors, "symbol_table": self.symbol_table}

        self.symbol_table = parse_result["symbol_table"]

        # 3. Проверка на неопределенные переменные
        self.check_variables(tokens)

        # 4. Проверка типов переменных
        self.check_types()

        return {
            "success": len(self.errors) == 0,
            "errors": self.errors,
            "symbol_table": self.symbol_table
        }

    def check_variables(self, tokens: List[Tuple[str, Any]]):
        """
        Проверка на использование переменных до их объявления.
        """
        # Сначала пройдем по всем токенам и добавим все переменные, объявленные с помощью 'let'
        for i, token in enumerate(tokens):
            if token[0] == "KEYWORD" and token[1] == "let":
                # Идентификатор, который объявляется после 'let'
                if i + 1 < len(tokens) and tokens[i + 1][0] == "IDENTIFIER":
                    identifier = tokens[i + 1][1]
                    self.declared_variables.add(identifier)  # Добавляем переменную в множество объявленных

        # Теперь проверим все использование переменных в программе
        for token in tokens:
            if token[0] == "IDENTIFIER":
                var_name = token[1]

                # Проверяем, была ли переменная объявлена
                if var_name not in self.declared_variables:
                    self.undeclared_usage.add(var_name)  # Отмечаем переменную как использованную до объявления

        # Ошибки использования переменных до объявления
        for var_name in self.undeclared_usage:
            self.errors.append(f"Переменная {var_name} используется до объявления.")

    def check_types(self):
        """
        Проверка типов переменных.
        """
        for var_name, info in self.symbol_table.items():
            if info.get("type") == "variable" and info.get("value") is not None:
                if isinstance(info["value"], int):
                    expected_type = "int"
                elif isinstance(info["value"], float):
                    expected_type = "float"
                else:
                    expected_type = "unknown"

                if expected_type == "unknown":
                    self.errors.append(f"Неизвестный тип для переменной {var_name}.")

def analyze_program(program: str) -> Dict[str, Any]:
    # Лексический анализ
    lexer = LexicalAnalyzer()
    tokens, lexical_errors = lexer.tokenize(program)

    # Синтаксический анализ
    parser = SyntaxAnalyzer(tokens)
    parse_result = parser.parse()

    # Семантический анализ
    semantic_analyzer = SemanticAnalyzer()
    semantic_result = semantic_analyzer.analyze(lexical_errors, parse_result, tokens)

    # Возвращаем результаты всех этапов анализа
    return {
        "tokens": tokens,
        "lexical_errors": lexical_errors,
        "parse_result": parse_result,
        "semantic_result": semantic_result
    }

if __name__ == "__main__":
    program = """
    {
        let x = 10;
        let y 20;
        let $z = 30; 
        if x < y then {
            output x;
        } else {
            output z;
        } 
    }
    """

    result = analyze_program(program)

    print("Анализ программы завершен:")

    print("\nТокены:")
    print(tabulate(result["tokens"], headers=["Тип", "Значение"]))

    if result["lexical_errors"]:
        print("\nЛексические ошибки:")
        for error in result["lexical_errors"]:
            print(f"  - {error}")

    if result["parse_result"]["success"]:
        print("\nСинтаксический анализ завершен успешно.")
    else:
        print("\nСинтаксический анализ завершился с ошибкой.")
        print(f"Ошибка: {result['parse_result']['error']}")

    print("\nСемантический анализ:")
    print(f"Успешно: {result['semantic_result']['success']}")

    print("\nТаблица символов:")
    print(tabulate(
        [[k, v["type"], v.get("value", "") or ""] for k, v in result["semantic_result"]["symbol_table"].items()],
        headers=["Переменная", "Тип", "Значение"]
    ))