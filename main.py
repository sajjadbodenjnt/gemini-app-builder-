from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.lang import Builder
from kivy.utils import get_color_from_hex
from kivy.core.window import Window

Window.size = (800, 600)

KV = """
<AICodeAssistantApp>:
    background_color: app.bg_color
    text_color: app.fg_color
    accent_color: app.accent_color
    input_background_color: app.input_bg_color
    code_block_color: app.code_block_color

    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: root.background_color
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "AI Code Assistant"
            size_hint_y: None
            height: dp(48)
            font_size: '24sp'
            color: root.text_color
            halign: 'center'
            valign: 'middle'
            text_size: self.size

        Label:
            text: "Paste Code or Error Here:"
            size_hint_y: None
            height: dp(30)
            halign: 'left'
            valign: 'middle'
            text_size: self.width, self.height
            color: root.text_color

        ScrollView:
            size_hint_y: 0.4
            TextInput:
                id: input_code
                hint_text: "Enter your code or error message..."
                multiline: True
                background_color: root.input_background_color
                foreground_color: root.text_color
                cursor_color: root.text_color
                font_name: 'RobotoMono'
                font_size: '14sp'
                padding: dp(10)
                tab_width: dp(4)
                text_selection: True

        Button:
            text: "Fix & Optimize"
            size_hint_y: None
            height: dp(50)
            background_normal: ''
            background_color: root.accent_color
            color: root.background_color # Text on button should contrast with accent
            font_size: '18sp'
            on_release: app.process_code()

        Label:
            text: "AI Assistant Output:"
            size_hint_y: None
            height: dp(30)
            halign: 'left'
            valign: 'middle'
            text_size: self.width, self.height
            color: root.text_color

        ScrollView:
            TextInput:
                id: output_result
                readonly: True
                multiline: True
                background_color: root.input_background_color
                foreground_color: root.text_color
                font_name: 'RobotoMono'
                font_size: '14sp'
                padding: dp(10)
                markup: True
                text: "Waiting for code analysis..."
                text_selection: True
"""

class AICodeAssistantApp(App):
    bg_color = get_color_from_hex('#282a36')
    fg_color = get_color_from_hex('#f8f8f2')
    accent_color = get_color_from_hex('#50fa7b')
    input_bg_color = get_color_from_hex('#44475a')
    code_block_color = get_color_from_hex('#6272a4') # Dracula comment color for code blocks
    error_color = get_color_from_hex('#ff5555')
    warning_color = get_color_from_hex('#ffb86c')
    info_color = get_color_from_hex('#bd93f9')

    def build(self):
        self.title = "AI Code Assistant"
        return Builder.load_string(KV)

    def process_code(self):
        input_text = self.root.ids.input_code.text
        output_widget = self.root.ids.output_result

        if not input_text.strip():
            output_widget.text = f"[color={self.error_color}][b]Error:[/b] Please enter some code or an error message to analyze.[/color]"
            return

        simulated_output = self._generate_simulated_response(input_text)
        output_widget.text = simulated_output

    def _generate_simulated_response(self, input_text):
        output = f"[color={self.accent_color}][b]AI Analysis Complete![/b][/color]\n\n"

        if "import os" in input_text and "os.system" in input_text:
            output += f"[color={self.warning_color}][b]Optimization Suggestion:[/b][/color] Avoid `os.system()` for security and cross-platform reasons. Consider `subprocess.run()` instead.\n"
            output += f"[color={self.fg_color}][b]Example Fix:[/b][/color]\n"
            output += f"[color={self.code_block_color}]\nimport subprocess\n# Old: os.system('ls -l')\nsubprocess.run(['ls', '-l'])\n[/color]\n\n"
        elif "for i in range(len(list)):" in input_text:
            output += f"[color={self.warning_color}][b]Optimization Suggestion:[/b][/color] Iterate directly over the list for better readability and performance.\n"
            output += f"[color={self.fg_color}][b]Example Fix:[/b][/color]\n"
            output += f"[color={self.code_block_color}]\nmy_list = [1, 2, 3]\n# Old: for i in range(len(my_list)): print(my_list[i])\nfor item in my_list: print(item)\n[/color]\n\n"
        elif "def my_func(arg):" in input_text and "pass" in input_text:
            output += f"[color={self.warning_color}][b]Fix Suggestion:[/b][/color] The function `my_func` currently does nothing. Add implementation or return a value.\n"
            output += f"[color={self.fg_color}][b]Example Fix:[/b][/color]\n"
            output += f"[color={self.code_block_color}]\ndef my_func(arg):\n    return arg * 2\n[/color]\n\n"
        elif "Error: NameError" in input_text or "undefined" in input_text:
            output += f"[color={self.error_color}][b]Possible Fix for NameError:[/b][/color] Ensure the variable or function you are trying to use is defined and spelled correctly before its first use. Check for typos or missing imports.\n\n"
        else:
            output += f"[color={self.info_color}][b]General Analysis:[/b][/color] The provided code looks generally good! Here are some common best practices:\n"
            output += "    - Ensure variable names are descriptive.\n"
            output += "    - Add comments for complex logic.\n"
            output += "    - Handle potential exceptions with `try-except` blocks.\n\n"

        output += f"[color={self.fg_color}][b]Original Input Context:[/b][/color]\n"
        output += f"[color={self.code_block_color}]\n{input_text}\n[/color]\n\n"
        output += f"[color={self.accent_color}]Always test the suggested changes thoroughly![/color]"
        return output

if __name__ == "__main__":
    AICodeAssistantApp().run()