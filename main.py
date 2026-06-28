import os
import sys
import json
import requests
import subprocess
import threading
import shutil
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.lang import Builder
from kivy.core.window import Window

# Set window size for desktop testing, will be overridden on mobile devices
Window.size = (dp(360), dp(640)) 

# KV Language String for modern, responsive UI
KV = """
#:import ScrollEffect kivy.effects.scroll.ScrollEffect

<ResponsiveLabel@Label>:
    size_hint_y: None
    height: self.texture_size[1]
    text_size: self.width, None
    markup: True

<OllamaKivyBuilderApp>:
    orientation: 'vertical'
    padding: dp(10)
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.1, 1 # Dark background
        Rectangle:
            pos: self.pos
            size: self.size

    # Input and controls section
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: dp(160) # Fixed height for input area
        spacing: dp(5)

        Label:
            text: "[b]Kivy Ollama Builder[/b]"
            font_size: '24sp'
            size_hint_y: None
            height: self.texture_size[1]
            color: 0.8, 0.8, 0.8, 1 # Light gray text
            halign: 'center'
            valign: 'middle'

        TextInput:
            id: idea_input
            hint_text: "Enter your Kivy app idea (e.g., 'A simple counter app')"
            multiline: True
            size_hint_y: 1
            background_color: 0.2, 0.2, 0.2, 1
            foreground_color: 0.9, 0.9, 0.9, 1
            cursor_color: 0.9, 0.9, 0.9, 1
            font_size: '16sp'
            padding: dp(10)
            hint_text_color: 0.6, 0.6, 0.6, 1

        BoxLayout:
            size_hint_y: None
            height: dp(40)
            spacing: dp(5)

            TextInput:
                id: ollama_model_input
                hint_text: "Ollama Model (e.g., codellama)"
                text: "codellama" # Default model
                size_hint_x: 0.7
                background_color: 0.2, 0.2, 0.2, 1
                foreground_color: 0.9, 0.9, 0.9, 1
                cursor_color: 0.9, 0.9, 0.9, 1
                font_size: '16sp'
                padding: dp(10)
                hint_text_color: 0.6, 0.6, 0.6, 1

            Button:
                text: "Generate Code"
                size_hint_x: 0.3
                on_release: app.generate_code()
                background_normal: ''
                background_color: 0.15, 0.45, 0.75, 1 # Blue button
                color: 1, 1, 1, 1
                font_size: '16sp'
                state_image: 'atlas://data/images/defaulttheme/button_pressed' if self.state == 'down' else 'atlas://data/images/defaulttheme/button'

    # Generated Code Display Section
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.4 # Takes proportional vertical space
        spacing: dp(5)

        Label:
            text: "[b]Generated Python Code:[/b]"
            size_hint_y: None
            height: self.texture_size[1]
            color: 0.8, 0.8, 0.8, 1
            font_size: '16sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.width, None

        ScrollView:
            size_hint_y: 1
            bar_width: dp(8)
            effect_cls: ScrollEffect
            background_color: 0.2, 0.2, 0.2, 1
            canvas.before:
                Color:
                    rgba: 0.15, 0.15, 0.15, 1 # Slightly lighter than background
                Rectangle:
                    pos: self.pos
                    size: self.size

            TextInput:
                id: generated_code_output
                readonly: True
                multiline: True
                size_hint_y: None
                height: self.minimum_height
                background_color: 0.15, 0.15, 0.15, 1 # Match ScrollView background
                foreground_color: 0.9, 0.9, 0.9, 1
                cursor_color: 0.9, 0.9, 0.9, 1
                font_name: 'RobotoMono-Regular' # Monospace font for code
                font_size: '14sp'
                padding: dp(10)
                bar_color: 0.4, 0.4, 0.4, 1
                bar_inactive_color: 0.3, 0.3, 0.3, 1
                bar_width: dp(8)

    # Buildozer Controls and Log Section
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.6 # Takes remaining vertical space
        spacing: dp(5)

        Button:
            text: "Save Code and Trigger Buildozer"
            size_hint_y: None
            height: dp(40)
            on_release: app.trigger_buildozer()
            background_normal: ''
            background_color: 0.25, 0.65, 0.35, 1 # Green button
            color: 1, 1, 1, 1
            font_size: '16sp'
            disabled: True # Disable until code is generated
            id: build_button
            state_image: 'atlas://data/images/defaulttheme/button_pressed' if self.state == 'down' else 'atlas://data/images/defaulttheme/button'

        Label:
            text: "[b]Buildozer Log:[/b]"
            size_hint_y: None
            height: self.texture_size[1]
            color: 0.8, 0.8, 0.8, 1
            font_size: '16sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.width, None

        ScrollView:
            size_hint_y: 1 # Fill remaining space in this BoxLayout
            bar_width: dp(8)
            effect_cls: ScrollEffect
            canvas.before:
                Color:
                    rgba: 0.15, 0.15, 0.15, 1
                Rectangle:
                    pos: self.pos
                    size: self.size

            ResponsiveLabel:
                id: build_log_output
                text: ""
                color: 0.7, 0.7, 0.7, 1
                font_name: 'RobotoMono-Regular' # Monospace font for logs
                font_size: '12sp'
                padding: dp(10)
                halign: 'left'
                valign: 'top'

        Label:
            id: status_label
            text: "Ready."
            size_hint_y: None
            height: self.texture_size[1]
            color: 1, 1, 0, 1 # Yellow status
            font_size: '14sp'
            halign: 'center'
            valign: 'middle'
            text_size: self.width, None
"""


class OllamaKivyBuilderApp(App):
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    # Create a directory for Kivy projects next to the script
    TEMP_PROJECT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kivy_projects")

    def build(self):
        self.title = "Kivy Ollama Builder"
        # Load the KV string
        Builder.load_string(KV)
        return BoxLayout(orientation='vertical') # Return a dummy root, actual widgets loaded by Builder.load_string

    def on_start(self):
        # Create the base directory for projects if it doesn't exist
        os.makedirs(self.TEMP_PROJECT_BASE_DIR, exist_ok=True)
        self.update_status("App started. Ensure Ollama server is running locally.")
        # Load a monospace font for code and logs (RobotoMono is usually available on Android/Kivy)
        # For desktop, you might need to ensure it's available or provide one.
        # Kivy's default font (Roboto) often has a monospace variant.
        # If not, you can provide a .ttf file in your app directory.
        if 'RobotoMono-Regular' not in App.get_running_app()._fonts:
             from kivy.core.text import LabelBase
             try:
                 # Try to load common monospace font paths or directly from data/fonts
                 LabelBase.register(name='RobotoMono-Regular',
                                    fn_regular='data/fonts/RobotoMono-Regular.ttf')
             except Exception:
                 # Fallback if font isn't found/registered, use a generic monospace
                 print("Warning: RobotoMono-Regular not found, falling back to default monospace.")

    def update_status(self, message, color=(1, 1, 0, 1)):  # Default yellow
        """Updates the status label on the main thread."""
        Clock.schedule_once(lambda dt: self._update_status_on_main_thread(message, color), 0)

    def _update_status_on_main_thread(self, message, color):
        self.root.ids.status_label.text = message
        self.root.ids.status_label.color = color

    def update_generated_code(self, code):
        """Updates the generated code TextInput on the main thread."""
        Clock.schedule_once(lambda dt: self._update_generated_code_on_main_thread(code), 0)

    def _update_generated_code_on_main_thread(self, code):
        self.root.ids.generated_code_output.text = code
        # Enable build button only if code is not empty
        self.root.ids.build_button.disabled = not bool(code.strip())
        if code.strip():
            self.update_status("Code generated. Review and click 'Save and Trigger Buildozer'.", (0, 1, 0, 1))  # Green success
        else:
            self.update_status("Code generation failed or returned empty. Check Ollama server and model.", (1, 0, 0, 1))  # Red error

    def append_log(self, message):
        """Appends a message to the build log on the main thread."""
        Clock.schedule_once(lambda dt: self._append_log_on_main_thread(message), 0)

    def _append_log_on_main_thread(self, message):
        current_log = self.root.ids.build_log_output.text
        self.root.ids.build_log_output.text = current_log + message + "\n"
        # Scroll to the bottom of the log
        self.root.ids.build_log_output.parent.scroll_y = 0

    def generate_code(self):
        """Initiates the code generation process in a separate thread."""
        user_idea = self.root.ids.idea_input.text.strip()
        ollama_model = self.root.ids.ollama_model_input.text.strip()

        if not user_idea:
            self.update_status("Please enter an idea.", (1, 0, 0, 1))
            return
        if not ollama_model:
            self.update_status("Please enter an Ollama model name (e.g., codellama).", (1, 0, 0, 1))
            return

        self.root.ids.build_button.disabled = True
        self.root.ids.generated_code_output.text = ""
        self.root.ids.build_log_output.text = "" # Clear previous logs
        self.update_status("Generating code with Ollama... This might take a moment.", (1, 1, 0, 1))
        self.append_log(f"--- Generating code for: '{user_idea}' using model '{ollama_model}' ---")

        threading.Thread(target=self._generate_code_thread, args=(user_idea, ollama_model)).start()

    def _generate_code_thread(self, user_idea, model_name):
        """Handles the actual interaction with the Ollama API."""
        prompt = (
            f"You are a helpful assistant that generates Kivy Python code. "
            f"The user will provide an idea. Generate a complete, single-file Kivy Python application "
            f"based on the idea. Do NOT include any explanations, comments, or extra text, just the "
            f"executable Python code. Make sure it uses modern Kivy syntax (e.g., App class, build method, "
            f"BoxLayout, kvlang for simple UI). User idea: '{user_idea}'"
        )
        data = {
            "model": model_name,
            "prompt": prompt,
            "stream": False # We want the full response at once
        }
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(self.OLLAMA_API_URL, headers=headers, data=json.dumps(data), timeout=300)  # 5 min timeout
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            result = response.json()
            generated_content = result.get('response', '').strip()

            # Attempt to extract only the Python code block if markdown is present
            if '' in generated_content:
                start_idx = generated_content.find('') + len('')
                end_idx = generated_content.find('', start_idx)
                if start_idx != -1 and end_idx != -1:
                    generated_content = generated_content[start_idx:end_idx].strip()
            elif '' in generated_content: # Handle generic code block without language specifier
                start_idx = generated_content.find('') + len('')
                end_idx = generated_content.find('', start_idx)
                if start_idx != -1 and end_idx != -1:
                    generated_content = generated_content[start_idx:end_idx].strip()

            self.update_generated_code(generated_content)
            self.append_log("--- Code generation complete ---")
        except requests.exceptions.ConnectionError:
            self.update_status("Error: Could not connect to Ollama. Is the server running?", (1, 0, 0, 1))
            self.append_log("Error: Could not connect to Ollama. Please ensure 'ollama serve' is running (e.g., in a separate terminal).")
            self.update_generated_code("")
        except requests.exceptions.Timeout:
            self.update_status("Error: Ollama request timed out.", (1, 0, 0, 1))
            self.append_log("Error: Ollama request timed out (5 minutes). The model might be too slow or the request too complex.")
            self.update_generated_code("")
        except requests.exceptions.RequestException as e:
            self.update_status(f"Error communicating with Ollama: {e}", (1, 0, 0, 1))
            self.append_log(f"Error communicating with Ollama: {e}. Check model name or Ollama server status.")
            self.update_generated_code("")
        except json.JSONDecodeError:
            self.update_status("Error: Invalid JSON response from Ollama.", (1, 0, 0, 1))
            self.append_log("Error: Invalid JSON response from Ollama. The server might have returned an unexpected format.")
            self.update_generated_code("")
        except Exception as e:
            self.update_status(f"An unexpected error occurred during code generation: {e}", (1, 0, 0, 1))
            self.append_log(f"An unexpected error occurred during code generation: {e}")
            self.update_generated_code("")

    def trigger_buildozer(self):
        """Initiates the Buildozer compilation process in a separate thread."""
        generated_code = self.root.ids.generated_code_output.text.strip()
        if not generated_code:
            self.update_status("No code to compile. Generate code first.", (1, 0, 0, 1))
            return

        self.root.ids.build_button.disabled = True
        self.update_status("Initializing Buildozer...", (1, 1, 0, 1))
        self.append_log("--- Starting Buildozer compilation ---")

        # Create a unique project directory for each compilation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        app_name_base = self.root.ids.idea_input.text.strip().replace(" ", "_").lower()
        if not app_name_base:
            app_name_base = "kivy_app"
        # Sanitize app_name_base to only include alphanumeric and underscores
        app_name_base = "".join(c for c in app_name_base if c.isalnum() or c == '_')
        project_dir_name = f"{app_name_base}_{timestamp}"
        project_path = os.path.join(self.TEMP_PROJECT_BASE_DIR, project_dir_name)

        threading.Thread(target=self._compile_apk_thread, args=(project_path, generated_code)).start()

    def _compile_apk_thread(self, project_path, main_py_content):
        """Handles the actual Buildozer commands."""
        original_cwd = os.getcwd() # Store original current working directory
        try:
            os.makedirs(project_path, exist_ok=True)
            self.append_log(f"Created project directory: [b]{project_path}[/b]")

            # Define app_title and package_name from the idea or a default
            idea_text = self.root.ids.idea_input.text.strip()
            app_title = idea_text if idea_text else "My Kivy Ollama App"
            # Sanitize for package name (lowercase, no spaces, no special chars)
            package_name = "".join(c for c in app_title.lower().replace(" ", "") if c.isalnum())
            if not package_name:
                package_name = "kivyollamaapp"

            self._create_project_files(project_path, main_py_content, app_title, package_name)
            self.append_log("Project files (main.py, buildozer.spec) created.")

            # Change directory to the project path for buildozer to find its spec file
            os.chdir(project_path)
            self.append_log(f"Changed current directory to: [b]{os.getcwd()}[/b]")

            # Run buildozer command
            # 'android debug deploy run' will build, install, and run on a connected device
            buildozer_command = ['buildozer', 'android', 'debug', 'deploy', 'run']
            self.append_log(f"Executing command: [b]{' '.join(buildozer_command)}[/b]")
            self.append_log("-" * 30)

            process = subprocess.Popen(
                buildozer_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout for unified log
                text=True,  # Decode as text (UTF-8 by default)
                bufsize=1  # Line-buffered output
            )

            for line in process.stdout:
                self.append_log(line.strip()) # Append each line of output to the log

            process.wait()  # Wait for the process to finish

            self.append_log("-" * 30)
            if process.returncode == 0:
                self.update_status("APK compiled, deployed, and run successfully!", (0, 1, 0, 1))
                self.append_log("[b]--- Buildozer compilation finished successfully ---[/b]")
                self.append_log(f"APK might be found in: [b]{project_path}/bin/[/b]")
            else:
                self.update_status(f"Buildozer failed with exit code {process.returncode}.", (1, 0, 0, 1))
                self.append_log(f"[b]--- Buildozer compilation failed with exit code {process.returncode} ---[/b]")

        except FileNotFoundError:
            self.update_status("Error: 'buildozer' command not found. Is Buildozer installed?", (1, 0, 0, 1))
            self.append_log("Error: 'buildozer' command not found. Please ensure Buildozer is installed and in your system PATH.")
        except Exception as e:
            self.update_status(f"An error occurred during compilation: {e}", (1, 0, 0, 1))
            self.append_log(f"An unexpected error occurred during Buildozer process: {e}")
        finally:
            # Always change back to the original directory
            os.chdir(original_cwd)
            self.append_log(f"Changed back to original directory: [b]{os.getcwd()}[/b]")
            self.root.ids.build_button.disabled = False  # Re-enable button after process

            # Optional: clean up the project directory after compilation
            # For debugging, it's often useful to keep the directory.
            # If you want to clean up, uncomment the following line:
            # shutil.rmtree(project_path)
            # self.append_log(f"Cleaned up project directory: {project_path}")


    def _create_project_files(self, project_dir, main_py_content, app_title, package_name):
        """Creates main.py and buildozer.spec files in the project directory."""
        main_py_path = os.path.join(project_dir, 'main.py')
        with open(main_py_path, 'w', encoding='utf-8') as f:
            f.write(main_py_content)

        spec_path = os.path.join(project_dir, 'buildozer.spec')
        buildozer_spec_content = f"""
[app]

# (str) Title of your application
title = {app_title}

# (str) Package name
package.name = {package_name}

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Application versioning (method 1 of 2)
version = 0.1

# (list) Source files to include (let empty to include all the files
# in the source dir)
source.include_ext = py,png,jpg,kv,atlas,mp3,ogg

# (str) Project directory. This is the directory that contains your main.py file.
# This defaults to the directory where buildozer.spec is located.
source.dir = .

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy

# (str) The orientation of the app
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,CAMERA,VIBRATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
# INTERNET is crucial for Ollama interaction if generated app needs it.
# CAMERA, VIBRATE, READ/WRITE_EXTERNAL_STORAGE are common and useful for many Kivy apps.

# (int) target Android API, should be 27 or higher. Buildozer usually picks latest available
# but specifying can override. Kivy generally recommends a higher API.
android.api = 33

# (int) Minimum API your app will run on.
android.minapi = 21

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (str) Path to your main.py file.
main.py = main.py
        """
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(buildozer_spec_content.strip())


if __name__ == '__main__':
    # Check for required libraries
    try:
        import requests
    except ImportError:
        print("Error: 'requests' library not found. Please install it: pip install requests")
        sys.exit(1)
    
    # Check if buildozer is installed and in PATH
    try:
        subprocess.run(['buildozer', '--version'], capture_output=True, check=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: 'buildozer' command not found or not working.")
        print("Please ensure Buildozer is installed and correctly configured in your PATH.")
        print("Install with: pip install buildozer")
        print("Then initialize buildozer once in a dummy project: buildozer init && buildozer android debug")
        sys.exit(1)

    try:
        OllamaKivyBuilderApp().run()
    except Exception as e:
        # Catch any unhandled Kivy or Python errors for better console feedback
        print(f"\nAn unhandled error occurred that crashed the Kivy app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)