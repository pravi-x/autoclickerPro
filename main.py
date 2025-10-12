import sys
import threading
import time
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import keyboard  # External global hotkey library
import ctypes
from ctypes import wintypes

# --- Windows ctypes setup ---
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


# Struct for mouse position
class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


# --- Helper functions ---
def get_mouse_position():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


def get_pixel_color(x, y):
    hdc = user32.GetDC(0)
    color = gdi32.GetPixel(hdc, x, y)
    user32.ReleaseDC(0, hdc)
    # Convert BGR to RGB
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    return (r, g, b)


def mouse_click(x, y, click_type="left"):
    user32.SetCursorPos(x, y)
    if click_type == "left":
        user32.mouse_event(2, 0, 0, 0, 0)  # Left button down
        user32.mouse_event(4, 0, 0, 0, 0)  # Left button up
    elif click_type == "right":
        user32.mouse_event(8, 0, 0, 0, 0)  # Right button down
        user32.mouse_event(16, 0, 0, 0, 0)  # Right button up
    elif click_type == "middle":
        user32.mouse_event(32, 0, 0, 0, 0)  # Middle button down
        user32.mouse_event(64, 0, 0, 0, 0)  # Middle button up
    # If click_type is "move", just move the cursor (no click)


def validate_and_parse_xy(text):
    text = text.strip()
    if not text:
        return None
    try:
        parts = text.split(",")
        if len(parts) != 2:
            return None
        x = int(parts[0].strip())
        y = int(parts[1].strip())
        return (x, y)
    except (ValueError, IndexError):
        return None


def parse_color(text):
    text = text.strip()
    if not text:
        return None
    try:
        parts = text.split(",")
        if len(parts) != 3:
            return None
        r = int(parts[0].strip())
        g = int(parts[1].strip())
        b = int(parts[2].strip())
        if all(0 <= val <= 255 for val in (r, g, b)):
            return (r, g, b)
        else:
            return None
    except (ValueError, IndexError):
        return None


def colors_close(col1, col2, tolerance=10):
    return all(abs(a - b) <= tolerance for a, b in zip(col1, col2))


# --- Main App ---
class AutoClickerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto Clicker Pro")
        self.geometry("950x750")
        self.wm_attributes("-topmost", 1)
        self.configure(bg="#2c3e50")

        self.running = False
        self.thread = None
        self.actions = []
        self.current_hotkey = None
        self.copy_pos_hotkey = None
        self.copy_color_hotkey = None

        # Configure styles
        self.setup_styles()

        # Create main canvas and scrollbar for scrolling
        self.canvas = tk.Canvas(self, bg="#2c3e50", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas, style="Main.TFrame")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack canvas and scrollbar
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bind mouse wheel to scroll
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # --- UI Setup ---
        main_frame = ttk.Frame(self.scrollable_frame, style="Main.TFrame", padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame, text="Auto Clicker Pro", style="Title.TLabel"
        )
        title_label.pack(pady=(0, 15))

        # Mouse info section
        self.create_mouse_info_section(main_frame)

        # Input section
        self.create_input_section(main_frame)

        # Action list section
        self.create_action_list_section(main_frame)

        # Monitor section
        self.create_monitor_section(main_frame)

        # Control buttons section
        self.create_control_section(main_frame)

        # ALL HOTKEYS/SHORTCUTS AT THE END
        self.create_all_shortcuts_section(main_frame)

        # Start info updates and default hotkeys
        self.update_info()
        self.register_hotkey()
        self.register_copy_shortcuts()

        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def setup_styles(self):
        style = ttk.Style()

        # Configure main frame
        style.configure("Main.TFrame", background="#2c3e50")

        # Title style
        style.configure(
            "Title.TLabel",
            background="#2c3e50",
            foreground="#ecf0f1",
            font=("Arial", 16, "bold"),
        )

        # Section title style
        style.configure(
            "Section.TLabel",
            background="#2c3e50",
            foreground="#3498db",
            font=("Arial", 11, "bold"),
        )

        # Regular label style
        style.configure(
            "Regular.TLabel",
            background="#2c3e50",
            foreground="#ecf0f1",
            font=("Arial", 9),
        )

        # Input label style
        style.configure(
            "Input.TLabel",
            background="#2c3e50",
            foreground="#e74c3c",
            font=("Arial", 9, "bold"),
        )

        # Shortcut label style
        style.configure(
            "Shortcut.TLabel",
            background="#2c3e50",
            foreground="#f39c12",
            font=("Arial", 9),
        )

        # Frame styles
        style.configure(
            "Section.TFrame", background="#34495e", relief="raised", borderwidth=2
        )
        style.configure("Input.TFrame", background="#2c3e50")

        # Button styles
        style.configure("Action.TButton", font=("Arial", 10, "bold"))
        style.configure("Start.TButton", font=("Arial", 10, "bold"))
        style.configure("Stop.TButton", font=("Arial", 10, "bold"))
        style.configure("Copy.TButton", font=("Arial", 9, "bold"))

        # Map button colors
        style.map(
            "Action.TButton",
            background=[
                ("active", "#5dade2"),
                ("pressed", "#2e86c1"),
                ("disabled", "#95a5a6"),
            ],
            foreground=[("disabled", "#ecf0f1")],
        )
        style.map(
            "Start.TButton",
            background=[
                ("active", "#58d68d"),
                ("pressed", "#229954"),
                ("disabled", "#95a5a6"),
            ],
            foreground=[("disabled", "#ecf0f1")],
        )
        style.map(
            "Stop.TButton",
            background=[
                ("active", "#e74c3c"),
                ("pressed", "#943126"),
                ("disabled", "#95a5a6"),
            ],
            foreground=[("disabled", "#ecf0f1")],
        )
        style.map(
            "Copy.TButton",
            background=[
                ("active", "#f39c12"),
                ("pressed", "#e67e22"),
                ("disabled", "#95a5a6"),
            ],
            foreground=[("disabled", "#ecf0f1")],
        )

    def create_mouse_info_section(self, parent):
        info_frame = ttk.Frame(parent, style="Section.TFrame", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            info_frame, text="📍 Live Mouse Information", style="Section.TLabel"
        ).pack(anchor="w")

        info_content = ttk.Frame(info_frame, style="Input.TFrame")
        info_content.pack(fill=tk.X, pady=(5, 0))

        # Position section
        pos_frame = ttk.Frame(info_content, style="Input.TFrame")
        pos_frame.pack(side=tk.LEFT, padx=10)

        self.position_var = tk.StringVar(value="Position: (0, 0)")
        ttk.Label(
            pos_frame, textvariable=self.position_var, style="Regular.TLabel"
        ).pack(side=tk.LEFT)
        ttk.Button(
            pos_frame,
            text="📋",
            command=self.copy_position,
            style="Copy.TButton",
            width=3,
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Color section
        color_frame = ttk.Frame(info_content, style="Input.TFrame")
        color_frame.pack(side=tk.LEFT, padx=10)

        self.color_var = tk.StringVar(value="Pixel Color: (0, 0, 0)")
        ttk.Label(
            color_frame, textvariable=self.color_var, style="Regular.TLabel"
        ).pack(side=tk.LEFT)
        ttk.Button(
            color_frame,
            text="📋",
            command=self.copy_color,
            style="Copy.TButton",
            width=3,
        ).pack(side=tk.LEFT, padx=(5, 0))

    def create_input_section(self, parent):
        input_frame = ttk.Frame(parent, style="Section.TFrame", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            input_frame, text="⚙️ Action Configuration", style="Section.TLabel"
        ).pack(anchor="w")

        # Create grid for inputs
        grid_frame = ttk.Frame(input_frame, style="Input.TFrame")
        grid_frame.pack(fill=tk.X, pady=(10, 0))

        # Configure grid columns to expand
        for i in range(6):
            grid_frame.columnconfigure(i, weight=1)

        # Labels
        ttk.Label(grid_frame, text="Action Name", style="Input.TLabel").grid(
            row=0, column=0, sticky="w", padx=5
        )
        ttk.Label(grid_frame, text="Click Type", style="Input.TLabel").grid(
            row=0, column=1, sticky="w", padx=5
        )
        ttk.Label(grid_frame, text="Position", style="Input.TLabel").grid(
            row=0, column=2, sticky="w", padx=5
        )
        ttk.Label(grid_frame, text="Delay (seconds)", style="Input.TLabel").grid(
            row=0, column=3, sticky="w", padx=5
        )
        ttk.Label(grid_frame, text="Monitor Position", style="Input.TLabel").grid(
            row=0, column=4, sticky="w", padx=5
        )
        ttk.Label(grid_frame, text="Target Color", style="Input.TLabel").grid(
            row=0, column=5, sticky="w", padx=5
        )

        # Input fields
        self.name_input = ttk.Entry(grid_frame, font=("Arial", 9))
        self.name_input.grid(row=1, column=0, sticky="ew", padx=5, pady=(3, 0))

        # Click type dropdown
        self.click_type_var = tk.StringVar(value="Left Click")
        self.click_type_dropdown = ttk.Combobox(
            grid_frame,
            textvariable=self.click_type_var,
            values=["Left Click", "Right Click", "Middle Click", "Move Only"],
            state="readonly",
            font=("Arial", 9),
            width=12,
        )
        self.click_type_dropdown.grid(row=1, column=1, sticky="ew", padx=5, pady=(3, 0))

        self.click_pos_input = ttk.Entry(grid_frame, font=("Arial", 9))
        self.click_pos_input.grid(row=1, column=2, sticky="ew", padx=5, pady=(3, 0))

        self.delay_input = ttk.Entry(grid_frame, font=("Arial", 9))
        self.delay_input.grid(row=1, column=3, sticky="ew", padx=5, pady=(3, 0))

        self.monitor_pos_input = ttk.Entry(grid_frame, font=("Arial", 9))
        self.monitor_pos_input.grid(row=1, column=4, sticky="ew", padx=5, pady=(3, 0))

        self.target_color_input = ttk.Entry(grid_frame, font=("Arial", 9))
        self.target_color_input.grid(row=1, column=5, sticky="ew", padx=5, pady=(3, 0))

        # Placeholder text examples
        ttk.Label(grid_frame, text="e.g. 'Button Click'", style="Regular.TLabel").grid(
            row=2, column=0, sticky="w", padx=5, pady=(2, 0)
        )
        ttk.Label(grid_frame, text="", style="Regular.TLabel").grid(
            row=2, column=1, sticky="w", padx=5, pady=(2, 0)
        )
        ttk.Label(grid_frame, text="e.g. '100,200'", style="Regular.TLabel").grid(
            row=2, column=2, sticky="w", padx=5, pady=(2, 0)
        )
        ttk.Label(grid_frame, text="e.g. '1.5'", style="Regular.TLabel").grid(
            row=2, column=3, sticky="w", padx=5, pady=(2, 0)
        )
        ttk.Label(grid_frame, text="e.g. '150,300' (opt)", style="Regular.TLabel").grid(
            row=2, column=4, sticky="w", padx=5, pady=(2, 0)
        )
        ttk.Label(grid_frame, text="e.g. '255,0,0' (opt)", style="Regular.TLabel").grid(
            row=2, column=5, sticky="w", padx=5, pady=(2, 0)
        )

        # Add action button
        self.add_action_button = ttk.Button(
            input_frame,
            text="➕ Add Action",
            command=self.add_action,
            style="Action.TButton",
        )
        self.add_action_button.pack(pady=(10, 0), fill=tk.X)

    def create_action_list_section(self, parent):
        list_frame = ttk.Frame(parent, style="Section.TFrame", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(list_frame, text="📋 Action Sequence", style="Section.TLabel").pack(
            anchor="w"
        )

        # Action list with scrollbar
        list_content = ttk.Frame(list_frame, style="Input.TFrame")
        list_content.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.action_list = tk.Listbox(
            list_content,
            height=6,
            bg="#34495e",
            fg="#ecf0f1",
            selectbackground="#3498db",
            selectforeground="#ffffff",
            font=("Arial", 9),
            relief="sunken",
            borderwidth=2,
        )

        self.action_scrollbar = ttk.Scrollbar(
            list_content, orient=tk.VERTICAL, command=self.action_list.yview
        )
        self.action_list.config(yscrollcommand=self.action_scrollbar.set)
        self.action_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.action_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def create_monitor_section(self, parent):
        monitor_frame = ttk.Frame(parent, style="Section.TFrame", padding="10")
        monitor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(monitor_frame, text="📺 Action Monitor", style="Section.TLabel").pack(
            anchor="w"
        )

        monitor_content = ttk.Frame(monitor_frame, style="Input.TFrame")
        monitor_content.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.monitor_text = tk.Text(
            monitor_content,
            height=6,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#2c3e50",
            fg="#1abc9c",
            insertbackground="#ecf0f1",
            selectbackground="#3498db",
            selectforeground="#ffffff",
            font=("Consolas", 9),
            relief="sunken",
            borderwidth=2,
        )

        monitor_scrollbar = ttk.Scrollbar(
            monitor_content, orient=tk.VERTICAL, command=self.monitor_text.yview
        )
        self.monitor_text.config(yscrollcommand=monitor_scrollbar.set)
        monitor_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.monitor_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def create_control_section(self, parent):
        control_frame = ttk.Frame(parent, style="Section.TFrame", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="🎮 Controls", style="Section.TLabel").pack(
            anchor="w"
        )

        # Repeat count
        repeat_frame = ttk.Frame(control_frame, style="Input.TFrame")
        repeat_frame.pack(fill=tk.X, pady=(10, 10))

        ttk.Label(
            repeat_frame, text="Repeat Count (0 for infinite):", style="Input.TLabel"
        ).pack(side=tk.LEFT, padx=5)
        self.repeat_input = ttk.Entry(repeat_frame, font=("Arial", 9), width=10)
        self.repeat_input.pack(side=tk.LEFT, padx=5)
        self.repeat_input.insert(0, "1")

        # File operations and control buttons
        button_frame = ttk.Frame(control_frame, style="Input.TFrame")
        button_frame.pack(fill=tk.X)

        self.save_button = ttk.Button(
            button_frame,
            text="💾 Save",
            command=self.save_actions,
            style="Action.TButton",
        )
        self.load_button = ttk.Button(
            button_frame,
            text="📂 Load",
            command=self.load_actions,
            style="Action.TButton",
        )
        self.start_button = ttk.Button(
            button_frame,
            text="▶️ Start",
            command=self.start_sequence,
            style="Start.TButton",
        )
        self.stop_button = ttk.Button(
            button_frame,
            text="⏹️ Stop",
            command=self.stop_sequence,
            style="Stop.TButton",
            state="disabled",
        )

        self.save_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.load_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.stop_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

    def create_all_shortcuts_section(self, parent):
        """Combined section for all keyboard shortcuts/hotkeys"""
        shortcuts_frame = ttk.Frame(parent, style="Section.TFrame", padding="10")
        shortcuts_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            shortcuts_frame, text="⌨️ Global Shortcuts & Hotkeys", style="Section.TLabel"
        ).pack(anchor="w")

        shortcuts_content = ttk.Frame(shortcuts_frame, style="Input.TFrame")
        shortcuts_content.pack(fill=tk.X, pady=(10, 0))

        # Start sequence hotkey
        start_hotkey_frame = ttk.Frame(shortcuts_content, style="Input.TFrame")
        start_hotkey_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(
            start_hotkey_frame, text="Start Sequence:", style="Input.TLabel"
        ).pack(side=tk.LEFT, padx=5)
        self.hotkey_input = ttk.Entry(start_hotkey_frame, font=("Arial", 9), width=15)
        self.hotkey_input.pack(side=tk.LEFT, padx=5)
        self.hotkey_input.insert(0, "alt+1")

        ttk.Button(
            start_hotkey_frame,
            text="🔧 Set",
            command=self.register_hotkey,
            style="Action.TButton",
            width=8,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            start_hotkey_frame, text="(Starts action sequence)", style="Shortcut.TLabel"
        ).pack(side=tk.LEFT, padx=5)

        # Position shortcut
        pos_shortcut_frame = ttk.Frame(shortcuts_content, style="Input.TFrame")
        pos_shortcut_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(pos_shortcut_frame, text="Copy Position:", style="Input.TLabel").pack(
            side=tk.LEFT, padx=5
        )
        self.pos_shortcut_input = ttk.Entry(
            pos_shortcut_frame, font=("Arial", 9), width=15
        )
        self.pos_shortcut_input.pack(side=tk.LEFT, padx=5)
        self.pos_shortcut_input.insert(0, "alt+5")

        ttk.Button(
            pos_shortcut_frame,
            text="🔧 Set",
            command=self.register_copy_shortcuts,
            style="Action.TButton",
            width=8,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            pos_shortcut_frame, text="(Copies: x,y)", style="Shortcut.TLabel"
        ).pack(side=tk.LEFT, padx=5)

        # Color shortcut
        color_shortcut_frame = ttk.Frame(shortcuts_content, style="Input.TFrame")
        color_shortcut_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(color_shortcut_frame, text="Copy Color:", style="Input.TLabel").pack(
            side=tk.LEFT, padx=5
        )
        self.color_shortcut_input = ttk.Entry(
            color_shortcut_frame, font=("Arial", 9), width=15
        )
        self.color_shortcut_input.pack(side=tk.LEFT, padx=5)
        self.color_shortcut_input.insert(0, "alt+6")

        ttk.Button(
            color_shortcut_frame,
            text="🔧 Set",
            command=self.register_copy_shortcuts,
            style="Action.TButton",
            width=8,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            color_shortcut_frame, text="(Copies: R,G,B)", style="Shortcut.TLabel"
        ).pack(side=tk.LEFT, padx=5)

    def copy_position(self):
        """Copy current mouse position to clipboard"""
        x, y = get_mouse_position()
        position_text = f"{x},{y}"
        self.clipboard_clear()
        self.clipboard_append(position_text)
        self.log_to_monitor(f"📋 Copied position to clipboard: {position_text}")

    def copy_color(self):
        """Copy current pixel color to clipboard"""
        x, y = get_mouse_position()
        color = get_pixel_color(x, y)
        color_text = f"{color[0]},{color[1]},{color[2]}"
        self.clipboard_clear()
        self.clipboard_append(color_text)
        self.log_to_monitor(f"📋 Copied color to clipboard: {color_text}")

    def register_copy_shortcuts(self):
        """Register global shortcuts for copying position and color"""
        # Remove old shortcuts
        if self.copy_pos_hotkey:
            try:
                keyboard.remove_hotkey(self.copy_pos_hotkey)
            except Exception:
                pass
        if self.copy_color_hotkey:
            try:
                keyboard.remove_hotkey(self.copy_color_hotkey)
            except Exception:
                pass

        # Register new shortcuts
        pos_shortcut = self.pos_shortcut_input.get().strip().lower()
        color_shortcut = self.color_shortcut_input.get().strip().lower()

        try:
            self.copy_pos_hotkey = keyboard.add_hotkey(pos_shortcut, self.copy_position)
            self.copy_color_hotkey = keyboard.add_hotkey(
                color_shortcut, self.copy_color
            )
            messagebox.showinfo(
                "Shortcuts",
                f"Shortcuts registered:\n• Position: {pos_shortcut}\n• Color: {color_shortcut}",
            )
        except Exception as e:
            messagebox.showwarning(
                "Shortcut Error", f"Failed to register shortcuts: {e}"
            )

    def log_to_monitor(self, message):
        """Add a message to the monitor section with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"

        def update_text():
            self.monitor_text.config(state=tk.NORMAL)
            self.monitor_text.insert(tk.END, full_message)
            self.monitor_text.see(tk.END)  # Auto-scroll to bottom
            self.monitor_text.config(state=tk.DISABLED)

        self.after(0, update_text)

    def clear_monitor(self):
        """Clear the monitor section"""

        def clear_text():
            self.monitor_text.config(state=tk.NORMAL)
            self.monitor_text.delete(1.0, tk.END)
            self.monitor_text.config(state=tk.DISABLED)

        self.after(0, clear_text)

    def update_info(self):
        try:
            x, y = get_mouse_position()
            self.position_var.set(f"Position: ({x}, {y})")
            color = get_pixel_color(x, y)
            self.color_var.set(f"Pixel Color: {color}")
        except Exception as e:
            print(f"Error updating info: {e}")
        self.after(100, self.update_info)

    def add_action(self):
        name_text = self.name_input.get().strip()
        click_type_text = self.click_type_var.get()
        click_text = self.click_pos_input.get().strip()
        delay_text = self.delay_input.get().strip()
        monitor_text = self.monitor_pos_input.get().strip()
        target_color_text = self.target_color_input.get().strip()

        error_message = ""

        # Map display names to internal values
        click_type_map = {
            "Left Click": "left",
            "Right Click": "right",
            "Middle Click": "middle",
            "Move Only": "move",
        }
        click_type = click_type_map.get(click_type_text, "left")

        click_coords = validate_and_parse_xy(click_text)
        if click_coords is None:
            error_message += "• Position must be x,y with numeric values.\n"

        delay_time = 0.5
        if delay_text:
            try:
                delay_time = float(delay_text)
                if delay_time < 0:
                    error_message += "• Delay must be non-negative.\n"
            except ValueError:
                error_message += "• Delay must be a number.\n"

        monitor_coords = None
        if monitor_text:
            monitor_coords = validate_and_parse_xy(monitor_text)
            if monitor_coords is None:
                error_message += "• Pixel to monitor must be x,y or empty.\n"

        target_color = None
        if target_color_text:
            target_color = parse_color(target_color_text)
            if target_color is None:
                error_message += "• Target color must be R,G,B (0-255) or empty.\n"

        if error_message:
            messagebox.showwarning("Input Error", error_message.strip())
            return

        if not name_text:
            name_text = f"Action {len(self.actions) + 1}"

        if monitor_coords and target_color:
            action_text = f"{name_text} - {click_type_text} {click_coords}, monitor {monitor_coords} for color {target_color}, delay {delay_time}s"
        elif monitor_coords:
            action_text = f"{name_text} - {click_type_text} {click_coords}, monitor {monitor_coords} for any color change, delay {delay_time}s"
        else:
            action_text = f"{name_text} - {click_type_text} {click_coords}, no monitoring, delay {delay_time}s"

        self.action_list.insert(tk.END, action_text)
        self.actions.append(
            (
                name_text,
                click_type,
                click_coords,
                monitor_coords,
                target_color,
                delay_time,
            )
        )

        # Clear inputs after adding
        self.name_input.delete(0, tk.END)
        self.click_type_var.set("Left Click")
        self.click_pos_input.delete(0, tk.END)
        self.delay_input.delete(0, tk.END)
        self.monitor_pos_input.delete(0, tk.END)
        self.target_color_input.delete(0, tk.END)

    def save_actions(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV Files", "*.csv")]
        )
        if not path:
            return
        try:
            with open(path, mode="w", newline="") as file:
                writer = csv.writer(file)
                for name, click_type, click, monitor, color, delay in self.actions:
                    row = [name, click_type, click[0], click[1]]
                    row += [monitor[0], monitor[1]] if monitor else ["", ""]
                    row += [color[0], color[1], color[2]] if color else ["", "", ""]
                    row += [delay]
                    writer.writerow(row)
            messagebox.showinfo("Success", f"Saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def load_actions(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            with open(path, mode="r") as file:
                reader = csv.reader(file)
                self.actions.clear()
                self.action_list.delete(0, tk.END)

                # Map for display names
                click_type_display = {
                    "left": "Left Click",
                    "right": "Right Click",
                    "middle": "Middle Click",
                    "move": "Move Only",
                }

                for row in reader:
                    if len(row) >= 4:
                        name = row[0] if row[0] else f"Action {len(self.actions) + 1}"
                        click_type = (
                            row[1]
                            if row[1] in ["left", "right", "middle", "move"]
                            else "left"
                        )
                        click_coords = (int(row[2]), int(row[3]))
                        monitor_coords = None
                        target_color = None
                        delay_time = 0.5
                        if len(row) >= 6 and row[4] and row[5]:
                            monitor_coords = (int(row[4]), int(row[5]))
                        if len(row) >= 9 and row[6] and row[7] and row[8]:
                            target_color = (int(row[6]), int(row[7]), int(row[8]))
                        if len(row) >= 10:
                            delay_time = float(row[9])

                        click_type_text = click_type_display.get(
                            click_type, "Left Click"
                        )

                        if monitor_coords and target_color:
                            action_text = f"{name} - {click_type_text} {click_coords}, monitor {monitor_coords} for color {target_color}, delay {delay_time}s"
                        elif monitor_coords:
                            action_text = f"{name} - {click_type_text} {click_coords}, monitor {monitor_coords} for any color change, delay {delay_time}s"
                        else:
                            action_text = f"{name} - {click_type_text} {click_coords}, no monitoring, delay {delay_time}s"
                        self.actions.append(
                            (
                                name,
                                click_type,
                                click_coords,
                                monitor_coords,
                                target_color,
                                delay_time,
                            )
                        )
                        self.action_list.insert(tk.END, action_text)
            messagebox.showinfo("Success", f"Loaded from {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")

    def start_sequence(self):
        if not self.actions:
            messagebox.showinfo("Info", "No actions to perform.")
            return
        if self.running:
            return
        repeat_text = self.repeat_input.get().strip()
        try:
            repeat_count = int(repeat_text) if repeat_text else 1
            if repeat_count < 0:
                messagebox.showwarning(
                    "Input Error", "Repeat count must be non-negative."
                )
                return
        except ValueError:
            messagebox.showwarning("Input Error", "Repeat count must be an integer.")
            return

        self.clear_monitor()
        self.log_to_monitor("🚀 Starting action sequence...")

        self.running = True
        self.start_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.thread = threading.Thread(
            target=self.run_actions, args=(repeat_count,), daemon=True
        )
        self.thread.start()

    def stop_sequence(self):
        if self.running:
            self.log_to_monitor("🛑 Stopping action sequence...")
        self.running = False
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"

    def run_actions(self, repeat_count):
        try:
            if repeat_count == 0:
                cycle = 1
                while self.running:
                    self.log_to_monitor(f"🔄 Starting infinite cycle #{cycle}")
                    self.execute_actions()
                    cycle += 1
            else:
                for cycle in range(1, repeat_count + 1):
                    if not self.running:
                        break
                    self.log_to_monitor(f"🔄 Starting cycle {cycle}/{repeat_count}")
                    self.execute_actions()

            if self.running:  # Completed normally
                self.log_to_monitor("✅ Action sequence completed successfully!")
        except Exception as e:
            self.log_to_monitor(f"❌ Error during execution: {e}")

        self.after(0, self.stop_sequence)

    def execute_actions(self):
        # Map for display names
        click_type_display = {
            "left": "Left Click",
            "right": "Right Click",
            "middle": "Middle Click",
            "move": "Move Only",
        }

        for i, (
            name,
            click_type,
            click_pos,
            monitor_pos,
            target_color,
            delay_time,
        ) in enumerate(self.actions, 1):
            if not self.running:
                break

            # Log the action being performed
            action_desc = click_type_display.get(click_type, "Left Click")
            self.log_to_monitor(
                f"🖱️ Action {i}: {name} - {action_desc} at ({click_pos[0]}, {click_pos[1]})"
            )
            mouse_click(click_pos[0], click_pos[1], click_type)

            # Monitor pixel if specified
            if monitor_pos:
                if target_color:
                    # Monitor for specific color change
                    self.log_to_monitor(
                        f"👁️ Monitoring pixel ({monitor_pos[0]}, {monitor_pos[1]}) for color {target_color}"
                    )
                    last_log_time = time.time()

                    while self.running and not colors_close(
                        get_pixel_color(*monitor_pos), target_color
                    ):
                        current_time = time.time()
                        if current_time - last_log_time >= 1.0:  # Log once per second
                            current_color = get_pixel_color(*monitor_pos)
                            self.log_to_monitor(
                                f"⏳ Waiting ({monitor_pos[0]}, {monitor_pos[1]}) with color {current_color} to become {target_color}"
                            )
                            last_log_time = current_time
                        time.sleep(0.1)

                    if self.running:
                        final_color = get_pixel_color(*monitor_pos)
                        self.log_to_monitor(
                            f"🎯 Color change detected! Pixel is now {final_color}"
                        )
                else:
                    # Monitor for any color change
                    initial_color = get_pixel_color(*monitor_pos)
                    self.log_to_monitor(
                        f"👁️ Monitoring pixel ({monitor_pos[0]}, {monitor_pos[1]}) for any color change (initial: {initial_color})"
                    )
                    last_log_time = time.time()

                    while (
                        self.running and get_pixel_color(*monitor_pos) == initial_color
                    ):
                        current_time = time.time()
                        if current_time - last_log_time >= 1.0:  # Log once per second
                            self.log_to_monitor(
                                f"⏳ Waiting ({monitor_pos[0]}, {monitor_pos[1]}) with color {initial_color} for any change"
                            )
                            last_log_time = current_time
                        time.sleep(0.1)

                    if self.running:
                        final_color = get_pixel_color(*monitor_pos)
                        self.log_to_monitor(
                            f"🎯 Color change detected! Pixel changed from {initial_color} to {final_color}"
                        )

            # Delay after action
            if delay_time > 0 and self.running:
                self.log_to_monitor(f"⏰ Waiting {delay_time} seconds...")
                time.sleep(delay_time)

    def register_hotkey(self):
        hotkey_str = self.hotkey_input.get().strip().lower()
        if self.current_hotkey:
            try:
                keyboard.remove_hotkey(self.current_hotkey)
            except Exception:
                pass
        try:
            self.current_hotkey = keyboard.add_hotkey(hotkey_str, self.start_sequence)
            messagebox.showinfo("Hotkey", f"Hotkey '{hotkey_str}' registered.")
        except Exception as e:
            messagebox.showwarning("Hotkey Error", f"Failed to register: {e}")

    def close_window(self):
        self.stop_sequence()
        keyboard.unhook_all()
        self.destroy()


if __name__ == "__main__":
    app = AutoClickerApp()
    app.mainloop()
