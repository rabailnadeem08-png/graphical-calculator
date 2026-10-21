import ast
import math
import operator
import tkinter as tk

# ---------------------------------------------------------------
# Safe expression evaluator (no eval(), so no arbitrary code runs)
# ---------------------------------------------------------------
BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("Invalid expression")

    if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("Exponent too large")
        return BIN_OPS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_eval_node(node.operand))

    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "sqrt" and len(node.args) == 1 and not node.keywords):
        value = _eval_node(node.args[0])
        if value < 0:
            raise ValueError("Cannot take square root of a negative number")
        return math.sqrt(value)

    raise ValueError("Invalid expression")


def safe_eval(expression):
    """Convert display symbols to Python operators and evaluate safely."""
    cleaned = (expression.replace("×", "*")
                         .replace("÷", "/")
                         .replace("−", "-")
                         .replace("^", "**"))
    tree = ast.parse(cleaned, mode="eval")  # raises SyntaxError if malformed
    result = _eval_node(tree)

    if isinstance(result, complex):
        raise ValueError("Result is not a real number")
    if isinstance(result, float) and (math.isnan(result) or math.isinf(result)):
        raise ValueError("Result is undefined")
    return result


def format_number(value):
    if isinstance(value, float):
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return format(value, ".10g")
    return str(value)


# ---------------------------------------------------------------
# GUI
# ---------------------------------------------------------------
class Calculator:
    OPERATORS = "+−×÷^%"

    BG = "#1e1e2e"
    DISPLAY_BG = "#11111b"
    BTN_NUM = "#313244"
    BTN_OP = "#fab387"
    BTN_FUNC = "#45475a"
    BTN_EQ = "#a6e3a1"

    def __init__(self, root):
        self.root = root
        self.root.title("Graphical Calculator")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        self.expr = ""
        self.just_evaluated = False
        self.has_error = False

        self.expr_var = tk.StringVar(value="0")
        self.preview_var = tk.StringVar(value="")

        self.build_display()
        self.build_buttons()
        self.build_history()
        self.bind_keys()

    # ---------- layout ----------
    def build_display(self):
        frame = tk.Frame(self.root, bg=self.DISPLAY_BG, padx=10, pady=10)
        frame.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=10, pady=(10, 5))

        self.preview_label = tk.Label(
            frame, textvariable=self.preview_var, anchor="e",
            font=("Arial", 12), bg=self.DISPLAY_BG, fg="#9399b2")
        self.preview_label.pack(fill="x")

        self.display_label = tk.Label(
            frame, textvariable=self.expr_var, anchor="e",
            font=("Consolas", 26, "bold"), bg=self.DISPLAY_BG, fg="white",
            width=16)
        self.display_label.pack(fill="x")

    def build_buttons(self):
        layout = [
            ["C", "⌫", "(", ")"],
            ["√", "^", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "−"],
            ["1", "2", "3", "+"],
            ["±", "0", ".", "="],
        ]
        for r, row in enumerate(layout, start=1):
            for c, label in enumerate(row):
                if label == "=":
                    color = self.BTN_EQ
                elif label in "÷×−+":
                    color = self.BTN_OP
                elif label in ("C", "⌫", "(", ")", "√", "^", "%", "±"):
                    color = self.BTN_FUNC
                else:
                    color = self.BTN_NUM
                fg = "#11111b" if label in "=÷×−+" else "white"

                btn = tk.Button(
                    self.root, text=label, font=("Arial", 16, "bold"),
                    bg=color, fg=fg, activebackground="#6c7086",
                    activeforeground="white", bd=0, width=5, height=2,
                    command=lambda t=label: self.press(t))
                btn.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")

        for c in range(4):
            self.root.grid_columnconfigure(c, weight=1)

    def build_history(self):
        tk.Label(self.root, text="History (double-click to reuse)",
                 bg=self.BG, fg="#9399b2", font=("Arial", 10)
                 ).grid(row=7, column=0, columnspan=4, sticky="w", padx=12, pady=(8, 0))

        self.history = tk.Listbox(
            self.root, height=5, bg=self.DISPLAY_BG, fg="white",
            font=("Consolas", 11), bd=0, highlightthickness=0,
            selectbackground="#45475a")
        self.history.grid(row=8, column=0, columnspan=4, sticky="ew", padx=10, pady=(2, 10))
        self.history.bind("<Double-Button-1>", self.reuse_history)

    def bind_keys(self):
        self.root.bind("<Key>", self.on_key)

    # ---------- display ----------
    def refresh(self):
        self.has_error_color(False)
        self.expr_var.set(self.expr if self.expr else "0")
        self.update_preview()

    def has_error_color(self, is_error):
        self.display_label.config(fg="#f38ba8" if is_error else "white")

    def update_preview(self):
        """Live result preview. Errors are silent here."""
        if not self.expr or self.just_evaluated:
            self.preview_var.set("")
            return
        try:
            self.preview_var.set("= " + format_number(safe_eval(self.expr)))
        except Exception:
            self.preview_var.set("")

    def show_error(self, message):
        self.has_error = True
        self.expr = ""
        self.just_evaluated = False
        self.expr_var.set(message)
        self.preview_var.set("")
        self.has_error_color(True)

    # ---------- input handling ----------
    def on_key(self, event):
        char, keysym = event.char, event.keysym
        keymap = {"*": "×", "/": "÷", "-": "−"}

        if keysym in ("Return", "KP_Enter") or char == "=":
            self.press("=")
        elif keysym == "BackSpace":
            self.press("⌫")
        elif keysym == "Escape" or char.lower() == "c":
            self.press("C")
        elif char in keymap:
            self.press(keymap[char])
        elif char and char in "0123456789.+^%()":
            self.press(char)

    def press(self, token):
        if token == "C":
            self.expr = ""
            self.has_error = False
            self.just_evaluated = False
            self.preview_var.set("")
            self.refresh()
            return

        if token == "=":
            self.evaluate()
            return

        # Clear an error message before accepting new input
        if self.has_error:
            self.expr = ""
            self.has_error = False

        if token == "⌫":
            if self.just_evaluated:
                self.expr = ""
            else:
                self.expr = self.expr[:-1]
            self.just_evaluated = False
            self.refresh()
            return

        if token == "±":
            self.toggle_sign()
            return

        if token == "√":
            self.start_new_if_needed(starts_new=True)
            self.expr += "sqrt("
            self.just_evaluated = False
            self.refresh()
            return

        if token in self.OPERATORS:
            if not self.expr and token not in "−":
                return  # an expression can't start with these
            # Replace a trailing operator instead of stacking two
            if self.expr and self.expr[-1] in self.OPERATORS and token != "−":
                self.expr = self.expr[:-1]
            elif self.expr and self.expr[-1] in self.OPERATORS and self.expr[-1] == "−":
                self.expr = self.expr[:-1]
            self.just_evaluated = False
            self.expr += token
            self.refresh()
            return

        # Digits, ".", "(", ")"
        self.start_new_if_needed(starts_new=token not in ")")
        self.expr += token
        self.just_evaluated = False
        self.refresh()

    def start_new_if_needed(self, starts_new):
        """After '=', typing a number starts fresh; an operator continues."""
        if self.just_evaluated and starts_new:
            self.expr = ""
        self.just_evaluated = False

    def toggle_sign(self):
        if not self.expr:
            return
        if self.expr.startswith("−(") and self.expr.endswith(")"):
            self.expr = self.expr[2:-1]
        else:
            self.expr = "−(" + self.expr + ")"
        self.just_evaluated = False
        self.refresh()

    # ---------- evaluation with error handling ----------
    def evaluate(self):
        if self.has_error or not self.expr:
            return

        try:
            result = safe_eval(self.expr)
            text = format_number(result)
            self.history.insert(0, f"{self.expr} = {text}")
            self.expr = text
            self.just_evaluated = True
            self.preview_var.set("")
            self.refresh()
        except ZeroDivisionError:
            self.show_error("Cannot divide by zero")
        except SyntaxError:
            self.show_error("Invalid expression")
        except OverflowError:
            self.show_error("Number too large")
        except RecursionError:
            self.show_error("Expression too complex")
        except ValueError as e:
            self.show_error(str(e))
        except Exception:
            self.show_error("Error")

    def reuse_history(self, event=None):
        selection = self.history.curselection()
        if not selection:
            return
        entry = self.history.get(selection[0])
        self.expr = entry.split(" = ")[0]
        self.has_error = False
        self.just_evaluated = False
        self.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    Calculator(root)
    root.mainloop()