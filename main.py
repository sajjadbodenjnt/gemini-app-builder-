import os
import sys
import threading
import subprocess
import shutil
import tempfile
from functools import partial

# KivyMD imports
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.toolbar import MDToolbar
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.scrollview import MDScrollView
from kivymd.toast import toast

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.utils import platform

# Conditional import for Ollama client
# This application is designed to run on a desktop environment
# where Ollama server and Buildozer are available.
# The Ollama client library is not expected to be packaged for Android.
OLLAMA_AVAILABLE = False
if platform == 'android':
    print("Running on Android. Ollama client is not supported for local generation on device.")
    print("This app is intended for use on a desktop environment with Ollama server and Buildozer.")
else:
    try:
        import ollama
        OLLAMA_AVAILABLE = True
    except ImportError:
        print("Ollama Python package not found. Code generation will be disabled.")
        print("Please install it on your desktop environment: pip install ollama")

# Global variables for Ollama model and default prompt
OLLAMA_MODEL = "phi3:mini" # Change to your preferred local model (e.g., llama3, codegemma, tinyllama)
# Ensure you have pulled the model using `ollama pull <model_name>` on your desktop.

INITIAL_PROMPT = """
You are an expert Python Kivy GUI developer.
Generate a complete, single-file Kivy GUI application in Python.
The application should be simple, functional, and demonstrate a core Kivy concept.
It must be runnable as `python main.py`.
The application should include:
- An `MDApp` class and an `MDScreen` for the main layout.
- A `MDToolbar` with a relevant title.
- A simple layout (e.g., `MDBoxLayout`).
- At least one interactive widget (e.g., `MDTextField`, `MDRectangleFlatButton`).
- An action that modifies a label or updates some part of the UI.
- Use KivyMD components for a modern, functional look.
- Keep the code concise and focused on the user's idea.
- Provide ONLY the complete, executable Python code inside a markdown python block.
- Do NOT include any explanations, extra text, comments beyond the app's internal logic, or markdown fences outside the main code block.
- Do NOT import `ollama`, `threading`, `subprocess`, `os`, `sys`, `shutil`, `tempfile` (as this is the *generated* app, not this builder app).
- Make sure the app can run by itself without external files or special setup.

Here is the user idea: "{user_idea}"
"""


KV_CODE = """
<MainScreen>:
    MDBoxLayout:
        orientation: 'vertical'

        MDToolbar:
            id: toolbar
            title: "Kivy Ollama Builder"
            elevation: 10
            md_bg_color: app.theme_cls.primary_color
            specific_text_color: app.theme_cls.text_color

        MDScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                spacing: dp(10)
                padding: dp(15)
                size_hint_y: None
                height: self.minimum_height

                MDLabel:
                    text: "Enter your Kivy App Idea:"
                    size_hint_y: None
                    height: self.texture_size[1]
                    theme_text_color: "Primary"

                MDTextField:
                    id: user_idea_input
                    hint_text: "E.g., 'A simple counter app with increment and decrement buttons.'"
                    mode: "rectangle"
                    multiline: True
                    max_height: dp(150) # Limit initial height
                    size_hint_y: None
                    height: max(dp(50), self.minimum_height) # Grow with content, but min height
                    padding_y: [dp(10), dp(10)]
                    padding_x: [dp(10), dp(10)]

                MDRectangleFlatButton:
                    id: generate_code_button
                    text: "Generate Kivy Code with Ollama"
                    on_release: app.generate_code()
                    pos_hint: {'center_x': 0.5}
                    md_bg_color: app.theme_cls.primary_color
                    specific_text_color: 1, 1, 1, 1

                MDProgressBar:
                    id: progress_bar
                    size_hint_x: 1
                    value: 0
                    height: dp(8)
                    pos_hint: {'center_x': 0.5}
                    color: app.theme_cls.primary_color
                    opacity: 0

                MDSpinner:
                    id: spinner_code
                    size_hint: None, None
                    size: dp(46), dp(46)
                    pos_hint: {'center_x': 0.5, 'center_y': 0.5}
                    active: False

                MDLabel:
                    text: "Generated Python Code:"
                    size_hint_y: None
                    height: self.texture_size[1]
                    theme_text_color: "Primary"

                MDTextField:
                    id: generated_code_output
                    hint_text: "Generated code will appear here..."
                    mode: "rectangle"
                    multiline: True
                    readonly: True
                    size_hint_y: None
                    height: dp(300) # Fixed height for code output
                    padding_y: [dp(10), dp(10)]
                    padding_x: [dp(10), dp(10)]

                MDRectangleFlatButton:
                    id: build_apk_button
                    text: "Build APK Offline with Buildozer"
                    on_release: app.build_apk()
                    pos_hint: {'center_x': 0.5}
                    md_bg_color: app.theme_cls.accent_color
                    specific_text_color: 1, 1, 1, 1
                    disabled: True # Enabled only after code is generated

                MDProgressBar:
                    id: build_progress_bar
                    size_hint_x: 1
                    value: 0
                    height: dp(8)
                    pos_hint: {'center_x': 0.5}
                    color: app.theme_cls.accent_color
                    opacity: 0

                MDSpinner:
                    id: spinner_build
                    size_hint: None, None
                    size: dp(46), dp(46)
                    pos_hint: {'center_x': 0.5, 'center_y': 0.5}
                    active: False

                MDLabel:
                    text: "Build Status / Output:"
                    size_hint_y: None
                    height: self.texture_size[1]
                    theme_text_color: "Primary"

                MDTextField:
                    id: build_output
                    hint_text: "Buildozer output will appear here..."
                    mode: "rectangle"
                    multiline: True
                    readonly: True
                    size_hint_y: None
                    height: dp(200) # Fixed height for build output
                    padding_y: [dp(10), dp(10)]
                    padding_x: [dp(10), dp(10)]

                MDLabel:
                    id: status_label
                    text: "Ready."
                    size_hint_y: None
                    height: self.texture_size[1]
                    halign: 'center'
                    theme_text_color: "Secondary"
                    padding_y: [dp(10), dp(10)]
"""

class MainScreen(MDScreen):
    pass

class KivyOllamaBuilder(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "BlueGrey"
        self.theme_cls.accent_palette = "DeepOrange"
        self.theme_cls.theme_style = "Dark" # Or "Light" for a brighter theme

        self.root = Builder.load_string(KV_CODE)
        self.app_dir = os.path.dirname(os.path.abspath(__file__))

        self._check_environment()
        return self.root

    def _check_environment(self):
        """Checks for Ollama client and Buildozer availability."""
        if not OLLAMA_AVAILABLE:
            self.update_status(
                "ERROR: Ollama Python package not found. Code generation disabled. "
                "Please install it: pip install ollama",
                color=(1,0,0,1)
            )
            self.root.ids.generate_code_button.disabled = True
            self.root.ids.user_idea_input.hint_text = "Ollama package not installed. Generation unavailable."
        else:
            self.update_status(f"Ollama package found. Using model: {OLLAMA_MODEL}")

        if not self._check_buildozer():
            self.update_status(
                "ERROR: Buildozer not found. Please install it (pip install buildozer) "
                "and ensure Android SDK/NDK are configured on your desktop.",
                color=(1,0,0,1)
            )
            self.root.ids.build_apk_button.disabled = True
        else:
            self.update_status("Buildozer found. Ready to build if code is generated.", color=(0,0.7,0,1))
            # build_apk_button is initially disabled and enabled only after code generation


    def update_status(self, message, color=(1,1,1,1)):
        """Thread-safe method to update the status label."""
        Clock.schedule_once(lambda dt: self._update_status_ui(message, color))

    def _update_status_ui(self, message, color):
        self.root.ids.status_label.text = message
        # self.root.ids.status_label.color = color # Uncomment if you want to change label color

    def update_code_output(self, code):
        """Thread-safe method to update the generated code text field."""
        Clock.schedule_once(lambda dt: self._update_code_output_ui(code))

    def _update_code_output_ui(self, code):
        self.root.ids.generated_code_output.text = code
        # Adjust height dynamically based on content, with a minimum height
        self.root.ids.generated_code_output.height = max(dp(300), self.root.ids.generated_code_output.texture_size[1] + dp(20))

    def append_build_output(self, line):
        """Thread-safe method to append a line to the build output text field."""
        Clock.schedule_once(lambda dt: self._append_build_output_ui(line))

    def _append_build_output_ui(self, line):
        self.root.ids.build_output.text += line + "\n"
        # Scroll to bottom to show latest output
        scroll_view_parent = self.root.ids.build_output.parent
        if isinstance(scroll_view_parent, MDBoxLayout): # Assuming the MDTextField is inside a layout that's in a ScrollView
             # This is a bit hacky, KivyMD's MDTextField doesn't directly expose scroll,
             # but its parent ScrollView (if exists) can be manipulated.
             # For now, it's just appending. A dedicated ScrollView around MDTextField might be better.
             pass # For now, let's just append. The user can scroll manually.

    def set_progress_bar(self, progress_id, value, visible=True):
        """Thread-safe method to update a progress bar."""
        Clock.schedule_once(lambda dt: self._set_progress_bar_ui(progress_id, value, visible))

    def _set_progress_bar_ui(self, progress_id, value, visible):
        pb = self.root.ids[progress_id]
        pb.value = value
        pb.opacity = 1 if visible else 0
        pb.height = dp(8) if visible else 0

    def set_spinner_active(self, spinner_id, active):
        """Thread-safe method to activate/deactivate a spinner."""
        Clock.schedule_once(lambda dt: self.root.ids[spinner_id].set_active(active))

    def _check_buildozer(self):
        """Checks if Buildozer command is available in PATH."""
        try:
            subprocess.run(["buildozer", "--version"], check=True, capture_output=True, text=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def generate_code(self):
        """Initiates the code generation process in a separate thread."""
        if not OLLAMA_AVAILABLE:
            toast("Ollama Python package is not installed on this system.")
            return
        if not self._check_ollama_server_status():
            toast("Ollama server is not running or accessible. Please start it.")
            self.update_status("ERROR: Ollama server not running. Please start it.", color=(1,0,0,1))
            return

        user_idea = self.root.ids.user_idea_input.text
        if not user_idea.strip():
            toast("Please enter your Kivy app idea before generating code.")
            return

        self.update_status("Generating code with Ollama...", color=(0,0.5,1,1))
        self.set_progress_bar('progress_bar', 0, True)
        self.set_spinner_active('spinner_code', True)
        self.root.ids.generate_code_button.disabled = True
        self.root.ids.build_apk_button.disabled = True
        self.root.ids.generated_code_output.text = ""
        self.root.ids.build_output.text = ""

        threading.Thread(target=self._generate_code_thread, args=(user_idea,)).start()

    def _check_ollama_server_status(self):
        """Attempts to connect to the Ollama server to verify its availability."""
        try:
            # A simple call that requires the server to be up
            ollama.list()
            return True
        except Exception as e:
            print(f"Ollama server check failed: {e}")
            return False

    def _generate_code_thread(self, user_idea):
        """Worker thread for Ollama code generation."""
        full_prompt = INITIAL_PROMPT.format(user_idea=user_idea)
        try:
            # Simulate progress since ollama.generate doesn't provide real-time token stream for non-streaming calls
            for i in range(1, 100):
                # Update UI periodically to show "progress"
                Clock.schedule_once(partial(self.set_progress_bar, 'progress_bar', i, True), 0.005 * (i/100)**2) # Non-linear progress simulation
            
            response = ollama.generate(model=OLLAMA_MODEL, prompt=full_prompt, stream=False)
            generated_code = response['response'].strip()

            # Clean up potential markdown code block fences ( ... )
            if generated_code.startswith(""):
                generated_code = generated_code[len(""):].strip()
            if generated_code.endswith(""):
                generated_code = generated_code[:-len("")].strip()

            self.update_code_output(generated_code)
            self.update_status("Code generated successfully! Ready to build APK.", color=(0,1,0,1))
            self.root.ids.build_apk_button.disabled = False # Enable build button

        except ollama.ResponseError as e:
            msg = f"Ollama Error: {e.error}"
            if "model" in e.error and "not found" in e.error:
                msg += f"\nPlease ensure model '{OLLAMA_MODEL}' is pulled (e.g., `ollama pull {OLLAMA_MODEL}`)."
            self.update_status(msg, color=(1,0,0,1))
            self.update_code_output(msg)
            self.root.ids.build_apk_button.disabled = True
            toast(msg)
        except Exception as e:
            self.update_status(f"An unexpected error occurred during code generation: {e}", color=(1,0,0,1))
            self.update_code_output(f"Error: {e}")
            self.root.ids.build_apk_button.disabled = True
            toast(f"Generation error: {e}")
        finally:
            self.set_progress_bar('progress_bar', 100, False)
            self.set_spinner_active('spinner_code', False)
            self.root.ids.generate_code_button.disabled = False


    def build_apk(self):
        """Initiates the APK build process in a separate thread."""
        generated_code = self.root.ids.generated_code_output.text
        if not generated_code.strip():
            toast("Please generate Kivy code first before attempting to build the APK.")
            return

        self.update_status("Starting APK build process with Buildozer...", color=(1,0.5,0,1))
        self.set_progress_bar('build_progress_bar', 0, True)
        self.set_spinner_active('spinner_build', True)
        self.root.ids.generate_code_button.disabled = True
        self.root.ids.build_apk_button.disabled = True
        self.root.ids.build_output.text = ""

        threading.Thread(target=self._build_apk_thread, args=(generated_code,)).start()

    def _build_apk_thread(self, generated_code):
        """Worker thread for Buildozer APK compilation."""
        temp_dir = None
        original_cwd = os.getcwd()
        try:
            # Create a temporary directory for the new Kivy app project
            temp_dir = tempfile.mkdtemp(prefix="kivy_ollama_app_")
            self.update_status(f"Created temporary project directory: {temp_dir}")

            # Write the generated Python code to main.py
            main_py_path = os.path.join(temp_dir, "main.py")
            with open(main_py_path, "w") as f:
                f.write(generated_code)
            self.update_status(f"Wrote main.py to {main_py_path}")

            # Create a minimal buildozer.spec file
            app_name = f"GeneratedKivyApp_{os.path.basename(temp_dir)}"
            package_name = f"org.example.generatedkivyapp{os.path.basename(temp_dir).replace('-', '_')}"

            spec_content = f"""
[app]
title = {app_name.replace('_', ' ')}
package.name = {package_name}
package.domain = org.example
source.dir = .
source.exclude_dirs = bin, .idea, .git, .buildozer
version = 0.1
requirements = python3,kivy,kivymd # Ensure KivyMD is included
# If you have specific Android SDK/NDK requirements or device architectures, uncomment and adjust:
# android.api = 33
# android.minapi = 21
# android.maxapi = 33
# android.arch = arm64-v8a,armeabi-v7a
# debug = 1
# log_level = 2
"""
            buildozer_spec_path = os.path.join(temp_dir, "buildozer.spec")
            with open(buildozer_spec_path, "w") as f:
                f.write(spec_content)
            self.update_status(f"Wrote buildozer.spec to {buildozer_spec_path}")

            # Change to the temporary directory so Buildozer runs in the correct context
            os.chdir(temp_dir)
            self.update_status(f"Changed current directory to {temp_dir}")
            self.append_build_output("\n--- Running Buildozer (this may take a while) ---")
            self.append_build_output(f"Command: buildozer android debug (in {temp_dir})")

            # Execute buildozer command
            process = subprocess.Popen(
                ["buildozer", "android", "debug"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stderr into stdout for easier display
                text=True,
                bufsize=1 # Line-buffered output
            )

            total_output_lines = 0
            for line in iter(process.stdout.readline, ''):
                self.append_build_output(line.strip())
                total_output_lines += 1
                # Update progress bar based on lines, a very rough estimation
                # A full build can have thousands of lines, so this is just for visual feedback.
                self.set_progress_bar('build_progress_bar', min(99, int((total_output_lines / 500) * 100)), True)

            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                self.update_status("APK built successfully!", color=(0,1,0,1))
                apk_path = self._find_apk_path(temp_dir)
                if apk_path:
                    self.append_build_output(f"\nAPK generated at: {apk_path}")
                    toast(f"APK generated: {apk_path}")
                else:
                    self.append_build_output("\nCould not determine final APK path. Check 'bin/' directory in temp folder.")
                    toast("APK generated, but path unknown.")
            else:
                self.update_status(f"Buildozer failed with code: {return_code}. Check output for details.", color=(1,0,0,1))
                self.append_build_output(f"\nBuildozer exited with error code {return_code}.")
                toast("APK build failed.")

        except FileNotFoundError:
            self.update_status("ERROR: 'buildozer' command not found. Is it installed and in your system PATH?", color=(1,0,0,1))
            self.append_build_output("ERROR: 'buildozer' command not found. Please ensure Buildozer is installed and configured (pip install buildozer).")
            toast("Buildozer command not found.")
        except Exception as e:
            self.update_status(f"An unexpected error occurred during build: {e}", color=(1,0,0,1))
            self.append_build_output(f"ERROR: {e}")
            toast(f"Build error: {e}")
        finally:
            # Change back to original directory regardless of success or failure
            os.chdir(original_cwd)
            self.set_progress_bar('build_progress_bar', 100, False)
            self.set_spinner_active('spinner_build', False)
            self.root.ids.generate_code_button.disabled = False
            
            # Re-enable build button only if there's generated code present
            if self.root.ids.generated_code_output.text.strip():
                self.root.ids.build_apk_button.disabled = False

            # Decide whether to keep or remove the temporary project directory
            if temp_dir and os.path.exists(temp_dir):
                # For debugging purposes, it's often useful to keep the temp directory
                # Uncomment the line below to automatically delete it
                # shutil.rmtree(temp_dir)
                self.append_build_output(f"Temporary directory '{temp_dir}' retained for inspection. Please delete manually if no longer needed.")


    def _find_apk_path(self, project_dir):
        """Attempts to find the generated APK file within the project's bin directory."""
        bin_dir = os.path.join(project_dir, 'bin')
        if os.path.exists(bin_dir):
            for filename in os.listdir(bin_dir):
                if filename.endswith('.apk'):
                    return os.path.abspath(os.path.join(bin_dir, filename))
        return None


if __name__ == '__main__':
    # When packaged to Android, the 'platform' utility will detect 'android'.
    # In such a scenario, the Ollama-related features are disabled as they require
    # a desktop environment and the Ollama server.
    KivyOllamaBuilder().run()