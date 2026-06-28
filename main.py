import sys
import threading
import requests
import json
import subprocess
import os
from functools import partial

# Kivy imports
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.utils import platform

# KivyMD imports
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.dialog import MDDialog
from kivymd.uix.scrollview import MDScrollView
from kivymd.theming import ThemeManager

# Optional: To ensure a monospaced font for code display,
# you might need to register it. KivyMD often includes RobotoMono,
# but if not, you'd need to provide the .ttf file.
# from kivy.core.text import LabelBase
# if not LabelBase.is_registered('RobotoMono'):
#     # You would need to ensure 'RobotoMono-Regular.ttf' is accessible
#     # e.g., in the same directory or a fonts directory.
#     # For simplicity in a single-file, we assume it's available or fallback is okay.
#     LabelBase.register(name="RobotoMono",
#                        fn_regular="RobotoMono-Regular.ttf")


# KV language string definition for the UI
KV = '''
#:import platform kivy.utils.platform
#:import os os

<OllamaBuildozerApp>:
    orientation: 'vertical'
    padding: dp(10)
    spacing: dp(10)
    
    # KivyMD Theme configuration
    md_bg_color: self.theme_cls.bg_normal
    
    MDLabel:
        text: "Ollama & Buildozer Helper"
        halign: 'center'
        font_style: 'H5'
        size_hint_y: None
        height: self.texture_size[1]
        padding_y: dp(5)

    MDTextField:
        id: ollama_host_input
        hint_text: "Ollama Host (e.g., http://localhost:11434)"
        mode: "rectangle"
        helper_text: "Enter the URL where Ollama server is running."
        helper_text_mode: "on_focus"
        text: app.ollama_host
        on_text: app.ollama_host = self.text
        size_hint_y: None
        height: dp(48)

    MDTextField:
        id: ollama_model_input
        hint_text: "Ollama Model (e.g., codellama, llama3)"
        mode: "rectangle"
        helper_text: "Enter the Ollama model to use for code generation."
        helper_text_mode: "on_focus"
        text: app.ollama_model
        on_text: app.ollama_model = self.text
        size_hint_y: None
        height: dp(48)

    MDTextField:
        id: user_idea_input
        hint_text: "Enter your Python code idea here..."
        mode: "rectangle"
        multiline: True
        required: True
        helper_text: "Example: 'A Python function to calculate factorial.'"
        helper_text_mode: "on_focus"
        size_hint_y: 0.3
        padding: dp(10) # Add internal padding
        max_height: dp(200) # Limit height for responsiveness on smaller screens

    MDBoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: dp(48)
        spacing: dp(10)
        padding: dp(5), 0 # Add some horizontal padding
        
        MDRaisedButton:
            text: "Generate Python Code (Ollama)"
            on_release: app.generate_code()
            md_bg_color: app.theme_cls.primary_color
            disabled: app.is_generating or app.is_compiling
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            size_hint_x: 0.8
            font_size: '14sp' if self.width < dp(200) else '16sp'

        MDSpinner:
            id: generate_spinner
            size_hint: None, None
            size: dp(48), dp(48)
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            active: app.is_generating
            opacity: 1 if app.is_generating else 0

    MDScrollView:
        id: code_scroll_view
        size_hint_y: 0.4
        MDTextField:
            id: generated_code_output
            hint_text: "Generated Python Code"
            mode: "fill"
            multiline: True
            readonly: True
            text: app.generated_code
            size_hint_y: None
            height: self.minimum_height # Automatically adjust height to content
            font_name: "RobotoMono" if platform != 'ios' and platform != 'android' else "monospace" # Use RobotoMono or fallback
            text_color: app.theme_cls.text_color
            line_color_normal: app.theme_cls.divider_color
            line_color_focus: app.theme_cls.primary_color
            fill_color: app.theme_cls.bg_normal
            padding: dp(10) # Add padding inside the textfield

    MDLabel:
        id: status_label
        text: app.status_message
        halign: 'left'
        size_hint_y: None
        height: self.texture_size[1]
        text_color: app.theme_cls.secondary_text_color
        padding_y: dp(5)

    MDBoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: dp(48)
        spacing: dp(10)
        padding: dp(5), 0 # Add some horizontal padding

        MDRaisedButton:
            text: "Compile Current App APK (Buildozer)"
            on_release: app.compile_apk()
            md_bg_color: app.theme_cls.accent_color
            # Disable if generating/compiling, if on Android, or if buildozer.spec is missing
            disabled: app.is_generating or app.is_compiling or platform == 'android' or not os.path.exists('buildozer.spec')
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            size_hint_x: 0.8
            font_size: '14sp' if self.width < dp(200) else '16sp'
            
        MDSpinner:
            id: compile_spinner
            size_hint: None, None
            size: dp(48), dp(48)
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            active: app.is_compiling
            opacity: 1 if app.is_compiling else 0
'''

class OllamaBuildozerApp(MDApp):
    """
    A KivyMD application that takes user ideas, generates Python code using
    a local Ollama server, and can trigger Buildozer to compile the *current*
    Kivy app into an APK (desktop only).
    """

    # Kivy properties for dynamic UI updates
    ollama_host = StringProperty("http://localhost:11434")
    ollama_model = StringProperty("codellama")
    generated_code = StringProperty("")
    status_message = StringProperty("Ready.")
    is_generating = BooleanProperty(False)
    is_compiling = BooleanProperty(False)
    
    dialog = None # Holds reference to the MDDialog for Android buildozer limitation

    def build(self):
        """Initializes the KivyMD application."""
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Orange"
        self.theme_cls.theme_style = "Dark" # Modern dark theme
        return Builder.load_string(KV)

    def generate_code(self):
        """
        Initiates the code generation process by sending the user's idea to Ollama
        in a separate thread.
        """
        user_idea = self.root.ids.user_idea_input.text
        if not user_idea.strip():
            self.status_message = "Please enter an idea to generate code."
            return

        self.is_generating = True
        self.status_message = "Generating code with Ollama..."
        self.generated_code = "" # Clear previous code
        
        # Run generation in a separate thread to keep the UI responsive
        threading.Thread(target=self._generate_code_ollama, args=(user_idea,)).start()

    def _generate_code_ollama(self, user_idea):
        """
        Private method to handle the actual API call to Ollama.
        Executed in a background thread.
        """
        ollama_url = f"{self.ollama_host}/api/generate"
        model = self.ollama_model.strip()
        
        if not model:
            model = "codellama" # Fallback if user clears model input

        # Craft a prompt to encourage Ollama to output only code
        prompt = (
            f"Generate a concise, self-contained Python script or function "
            f"based on the following idea. Provide only the executable Python code, "
            f"no explanations, no extra text, just the code. Ensure it's syntactically correct.\n\nIdea: {user_idea}"
        )

        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False, # Get the full response at once
            "options": {
                "temperature": 0.7, # A bit creative but focused
                "num_ctx": 4096   # Context window size for Ollama
            }
        }

        try:
            response = requests.post(ollama_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            
            data = response.json()
            generated_text = data.get("response", "").strip()

            # Post-process to extract only code if the model wraps it in markdown
            if generated_text.startswith(""):
                # Find the end of the code block
                end_index = generated_text.rfind("")
                if end_index > 3: # Ensure there's content between the markdown fences
                    # Try to remove language specifier (e.g., python) if present
                    first_line_end = generated_text.find('\n')
                    if first_line_end != -1 and "python" in generated_text[:first_line_end].lower():
                        generated_text = generated_text[first_line_end+1:end_index].strip()
                    else:
                        generated_text = generated_text[3:end_index].strip()
                else: # Only starts with , no closing fence or no content
                    generated_text = generated_text[3:].strip() # Just remove the opening fence
            
            # Update UI on the main thread
            Clock.schedule_once(lambda dt: self._update_generated_code(generated_text), 0)
            Clock.schedule_once(lambda dt: self._update_status("Code generation complete."), 0)

        except requests.exceptions.ConnectionError:
            Clock.schedule_once(lambda dt: self._update_status(
                "Error: Could not connect to Ollama. Make sure Ollama server is running and accessible at "
                f"{self.ollama_host}. For Android, use your desktop's local IP, not localhost."
            ), 0)
        except requests.exceptions.Timeout:
            Clock.schedule_once(lambda dt: self._update_status("Error: Ollama request timed out (60 seconds)."), 0)
        except requests.exceptions.RequestException as e:
            Clock.schedule_once(lambda dt: self._update_status(f"Error communicating with Ollama: {e}"), 0)
        except json.JSONDecodeError:
            Clock.schedule_once(lambda dt: self._update_status("Error: Ollama response was not valid JSON."), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._update_status(f"An unexpected error occurred during Ollama generation: {e}"), 0)
        finally:
            Clock.schedule_once(lambda dt: setattr(self, 'is_generating', False), 0) # Ensure spinner stops

    def _update_generated_code(self, code):
        """Updates the generated_code property on the main thread."""
        self.generated_code = code

    def _update_status(self, message):
        """Updates the status_message property on the main thread."""
        self.status_message = message

    def compile_apk(self):
        """
        Triggers the Buildozer compilation process for the *current* Kivy application.
        This function is designed to run only on a desktop environment with Buildozer installed.
        """
        # --- IMPORTANT LIMITATION ---
        # Buildozer runs on desktop operating systems (Linux, macOS, Windows with WSL)
        # to compile Kivy apps into APKs. It cannot be run from an Android device itself.
        if platform == 'android':
            self.show_android_buildozer_dialog()
            return
        # --- END IMPORTANT LIMITATION ---

        if not os.path.exists('buildozer.spec'):
            self.status_message = "Error: 'buildozer.spec' not found in the current directory. Cannot compile. " \
                                  "Run 'buildozer init' first."
            return

        self.is_compiling = True
        self.status_message = "Starting APK compilation with Buildozer (this may take a while)..."
        
        # Run compilation in a separate thread to keep UI responsive
        threading.Thread(target=self._compile_apk_buildozer).start()

    def _compile_apk_buildozer(self):
        """
        Private method to execute Buildozer commands.
        Executed in a background thread.
        """
        try:
            # Command to clean and then build a debug APK.
            # This assumes 'buildozer' is in your system PATH and 'buildozer.spec'
            # exists in the current working directory of the desktop app.
            build_command = ["buildozer", "android", "debug", "verbose"] # 'verbose' for more output

            # Use Popen to stream output from Buildozer process
            process = subprocess.Popen(
                build_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Redirect stderr to stdout for easier logging
                text=True,                 # Decode output as text
                bufsize=1,                 # Line-buffered output
                universal_newlines=True    # Handle different newline characters
            )

            # Read output line by line and update status on the main thread
            for line in process.stdout:
                Clock.schedule_once(partial(self._update_status_from_process, line.strip()), 0)
            
            process.wait() # Wait for the Buildozer process to complete

            if process.returncode == 0:
                Clock.schedule_once(lambda dt: self._update_status("APK compilation successful! Check 'bin/' folder."), 0)
            else:
                Clock.schedule_once(lambda dt: self._update_status(f"APK compilation failed with exit code {process.returncode}. Please check the console output."), 0)

        except FileNotFoundError:
            Clock.schedule_once(lambda dt: self._update_status(
                "Error: 'buildozer' command not found. "
                "Please ensure Buildozer is installed and in your system's PATH on your desktop."
            ), 0)
        except subprocess.CalledProcessError as e:
            Clock.schedule_once(lambda dt: self._update_status(
                f"Buildozer command failed: {e.output}"
            ), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._update_status(f"An unexpected error occurred during compilation: {e}"), 0)
        finally:
            Clock.schedule_once(lambda dt: setattr(self, 'is_compiling', False), 0) # Ensure spinner stops

    def _update_status_from_process(self, line, dt):
        """
        Updates the status message with output from the Buildozer process.
        This is called on the main thread for each line of output.
        """
        # For simplicity, we just show the latest line from Buildozer.
        # A real-world app might collect all output in a scrollable log.
        self.status_message = f"Buildozer: {line}"


    def show_android_buildozer_dialog(self):
        """Displays a dialog explaining why Buildozer cannot run on Android."""
        if not self.dialog:
            self.dialog = MDDialog(
                title="Buildozer Not Supported on Android",
                text="The 'Compile APK' function requires Buildozer, which runs exclusively on desktop operating systems "
                     "(Linux, macOS, Windows with WSL) to compile Kivy apps. This function cannot be executed directly "
                     "on an Android device.",
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=self.close_dialog
                    )
                ],
            )
        self.dialog.open()

    def close_dialog(self, obj):
        """Closes the currently open MDDialog."""
        if self.dialog:
            self.dialog.dismiss()

if __name__ == '__main__':
    OllamaBuildozerApp().run()