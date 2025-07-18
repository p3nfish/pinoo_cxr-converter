import os
import sys
import subprocess
import threading
import configparser
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from ttkbootstrap.scrolled import ScrolledFrame

APP_NAME = "Pinoo Script - CXR Converter"
CONFIG_FILENAME = "pinoo_script.cfg"
DONATE_LINK = "https://t.me/PinooScript"

COLOR_BG = "#282E33"
COLOR_ACCENT = "#009687"
COLOR_DANGER = "#ee5555"

COMMON_CORONA_PATHS = [
    r"C:\Program Files\Corona\Corona Renderer for 3ds Max\Image Editor\CoronaImageCmd.exe",
    r"C:\Program Files\Corona\Corona Renderer for 3ds Max\CoronaImageCmd.exe",
    r"C:\Program Files\Corona Renderer for 3ds Max\CoronaImageCmd.exe",
    r"C:\Program Files\Corona\CoronaImageCmd.exe",
    r"C:\Program Files\Chaos\Corona\Corona Renderer for 3ds Max\Image Editor\CoronaImageCmd.exe"
]

SUPPORTED_FORMATS = ["jpg", "png", "exr"]

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class PortableConfig:
    def __init__(self, path):
        self.path = path
        self.cp = configparser.ConfigParser()
        self.cp.read(self.path, encoding="utf-8")

    def get(self, section, key, default=None):
        return self.cp.get(section, key, fallback=default)

    def set(self, section, key, value):
        if not self.cp.has_section(section):
            self.cp.add_section(section)
        self.cp.set(section, key, value)
        with open(self.path, "w", encoding="utf-8") as f:
            self.cp.write(f)

class MultiSelectFrame(tb.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.items = []
        self.selected_indices = set()
        self.last_clicked_index = None

    def add_item(self, item_widget, item_data):
        item_widget.bind("<Button-1>", lambda e, i=len(self.items): self.on_click(e, i))
        item_widget.pack(anchor="w", padx=10)
        self.items.append({"widget": item_widget, "data": item_data})

    def on_click(self, event, index):
        if event.state & 0x0004:  # Control key
            if index in self.selected_indices:
                self.selected_indices.remove(index)
            else:
                self.selected_indices.add(index)
        elif event.state & 0x0001:  # Shift key
            if self.last_clicked_index is not None:
                start = min(self.last_clicked_index, index)
                end = max(self.last_clicked_index, index)
                for i in range(start, end + 1):
                    self.selected_indices.add(i)
        else:
            self.selected_indices.clear()
            self.selected_indices.add(index)
        
        self.last_clicked_index = index
        self.update_selection_visuals()

    def update_selection_visuals(self):
        for i, item in enumerate(self.items):
            if i in self.selected_indices:
                item["widget"].configure(bootstyle="info")
            else:
                item["widget"].configure(bootstyle="secondary")

    def get_selected_data(self):
        return [self.items[i]["data"] for i in self.selected_indices]

    def clear(self):
        for item in self.items:
            item["widget"].destroy()
        self.items.clear()
        self.selected_indices.clear()
        self.last_clicked_index = None

class PinooCXRApp(tb.Frame):
    def __init__(self, master):
        super().__init__(master, padding=15)
        self.pack(fill=BOTH, expand=YES)
        self.config = PortableConfig(os.path.join(get_app_dir(), CONFIG_FILENAME))
        self.corona_cmd = None
        self.corona_cmd_dir = self.config.get("main", "corona_cmd_dir")
        self.last_cxr_dirs = self.config.get("main", "last_cxr_dirs", default="").split(";")
        self.last_cxr_dirs = [path for path in self.last_cxr_dirs if os.path.isdir(path)]
        self.file_vars = []
        self.folder_path = tb.StringVar()
        self.config_file = None

        self.build_styles()
        self.build_gui()
        self.auto_find_corona_cmd()
        self.load_settings()

    def build_styles(self):
        style = tb.Style.get_instance()
        style.configure('TFrame', background=COLOR_BG)
        style.configure('TLabel', background=COLOR_BG, foreground='white')
        style.configure('TCheckbutton', background=COLOR_BG, foreground='white')
        style.configure('Accent.TButton', background=COLOR_ACCENT, foreground='white', font=("Segoe UI", 12, "bold"), borderwidth=0, focusthickness=1)
        style.map('Accent.TButton', background=[('active', '#13b7a7'), ('!active', COLOR_ACCENT)])
        style.configure('Icon.TButton', background=COLOR_BG, foreground=COLOR_ACCENT, borderwidth=1, relief="solid", padding=5)
        style.map('Icon.TButton', background=[('active', '#333')], foreground=[('active', '#fff')])

    def auto_find_corona_cmd(self):
        paths = COMMON_CORONA_PATHS.copy()
        if self.corona_cmd_dir and os.path.isdir(self.corona_cmd_dir):
            for f in os.listdir(self.corona_cmd_dir):
                if f.lower() == "coronaimagecmd.exe":
                    paths.insert(0, os.path.join(self.corona_cmd_dir, f))
        for path in paths:
            if os.path.isfile(path):
                self.set_corona_cmd(path)
                return
        self.set_corona_cmd(None)

    def set_corona_cmd(self, path):
        self.corona_cmd = path
        self.update_cmd_status()

    def build_gui(self):
        # CoronaImageCmd status line
        self.cmd_status_var = tb.StringVar()
        self.cmd_status_btn = tb.Button(self, textvariable=self.cmd_status_var, command=self.choose_corona_cmd, bootstyle="secondary-outline")
        self.cmd_status_btn.pack(fill=X, pady=(0, 10))

        # File list (new implementation)
        self.file_list_frame = ScrolledFrame(self, autohide=True)
        self.file_list_frame.pack(fill=BOTH, expand=YES, pady=5)
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)
        self.file_list = MultiSelectFrame(self.file_list_frame)
        self.file_list.pack(fill=BOTH, expand=YES)

        self.placeholder_label = tb.Label(self.file_list_frame, text="Drag&drop .cxr files or choose folder in explorer", font=("Segoe UI", 14), foreground="gray")
        self.placeholder_label.pack(pady=100, padx=10, expand=YES)
        self.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.dnd_bind('<<DragLeave>>', self.on_drag_leave)

        # Folder selection row
        folder_row = tb.Frame(self)
        folder_row.pack(fill=X, pady=5)
        tb.Button(folder_row, text="✓", command=self.toggle_all, width=3, bootstyle="secondary-outline").pack(side=LEFT, padx=(0, 5))
        self.folder_menu = tb.Combobox(folder_row, textvariable=self.folder_path, values=self.last_cxr_dirs, state="readonly")
        self.folder_menu.pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
        self.folder_menu.bind("<<ComboboxSelected>>", self.on_folder_select)
        tb.Button(folder_row, text="📂", command=self.select_folder, width=3, bootstyle="secondary-outline").pack(side=LEFT, padx=(0, 5))
        tb.Button(folder_row, text="❌", command=self.clear_all, width=3, bootstyle="danger-outline").pack(side=LEFT)

        # Options row
        opts_row = tb.Frame(self)
        opts_row.pack(fill=X, pady=5)
        tb.Label(opts_row, text="Format:", width=8).pack(side=LEFT)
        self.format_var = tb.StringVar(value="jpg")
        tb.Combobox(opts_row, textvariable=self.format_var, values=SUPPORTED_FORMATS, state="readonly", width=8).pack(side=LEFT, padx=(0, 10))
        self.beauty_only_var = tb.BooleanVar(value=True)
        tb.Checkbutton(opts_row, text="only BEAUTY", variable=self.beauty_only_var, bootstyle="info").pack(side=LEFT, padx=(0, 12))
        self.config_btn = tb.Button(opts_row, text="Choose .conf", command=self.select_config, bootstyle="secondary-outline")
        self.config_btn.pack(side=LEFT)

        # Progress and Convert
        self.progress_bar = tb.Progressbar(self, orient=HORIZONTAL, mode="determinate", bootstyle="info-striped")
        self.progress_bar.pack(fill=X, pady=10)
        self.convert_btn = tb.Button(self, text="Convert", command=self.start_conversion, bootstyle="Accent.TButton")
        self.convert_btn.pack(fill=X, ipady=8, pady=(0, 5))
        self.status_label = tb.Label(self, text="", font=("Segoe UI", 10))
        self.status_label.pack(fill=X)

        # Donate
        tb.Button(self, text="💸 Buy me a coffee", command=lambda: os.system(f'start {DONATE_LINK}'), bootstyle="warning-outline").pack(fill=X, pady=(15, 0))

    def load_settings(self):
        self.format_var.set(self.config.get("main", "format", "jpg"))
        self.beauty_only_var.set(self.config.get("main", "beauty_only", "true").lower() == "true")
        conf_path = self.config.get("main", "conf_path")
        if conf_path and os.path.isfile(conf_path):
            self.config_file = conf_path
            self.config_btn.config(bootstyle="success-outline")
        else:
            self.config_btn.config(bootstyle="secondary-outline")


    def save_settings(self):
        self.config.set("main", "last_cxr_dirs", ";".join(self.last_cxr_dirs))
        self.config.set("main", "format", self.format_var.get())
        self.config.set("main", "beauty_only", str(self.beauty_only_var.get()))
        self.config.set("main", "conf_path", self.config_file or "")

    def update_cmd_status(self):
        if self.corona_cmd and os.path.isfile(self.corona_cmd):
            self.cmd_status_var.set(f"CoronaImageCmd.exe – valid, ok!")
            self.cmd_status_btn.config(bootstyle="secondary-outline")
            self.convert_btn.config(state="normal")
        else:
            self.cmd_status_var.set("CoronaImageCmd.exe – invalid, choose from explorer!")
            self.cmd_status_btn.config(bootstyle="danger-outline")
            self.convert_btn.config(state="disabled")

    def choose_corona_cmd(self):
        start_dir = self.corona_cmd_dir if self.corona_cmd_dir and os.path.isdir(self.corona_cmd_dir) else ""
        exe_path = filedialog.askopenfilename(
            title="Choose CoronaImageCmd.exe",
            initialdir=start_dir,
            filetypes=[("CoronaImageCmd.exe", "*.exe")]
        )
        if exe_path and os.path.basename(exe_path).lower() == "coronaimagecmd.exe":
            self.set_corona_cmd(exe_path)
            self.corona_cmd_dir = os.path.dirname(exe_path)
            self.config.set("main", "corona_cmd_dir", self.corona_cmd_dir)

    def select_config(self):
        path = filedialog.askopenfilename(
            title="Choose .conf file",
            initialdir=self.folder_path.get() or (self.last_cxr_dirs[0] if self.last_cxr_dirs else ""),
            filetypes=[("Corona Config", "*.conf")]
        )
        if path:
            self.config_file = path
            self.config_btn.config(bootstyle="success-outline")
        else:
            self.config_file = None
            self.config_btn.config(bootstyle="secondary-outline")

    def on_folder_select(self, event=None):
        self.load_file_list()

    def select_folder(self):
        init_dir = self.last_cxr_dirs[0] if self.last_cxr_dirs else ""
        folder = filedialog.askdirectory(title="Choose folder with .cxr files", initialdir=init_dir)
        if not folder:
            return
        self.folder_path.set(folder)
        if folder not in self.last_cxr_dirs:
            self.last_cxr_dirs.insert(0, folder)
            self.last_cxr_dirs = self.last_cxr_dirs[:5]
            self.folder_menu.config(values=self.last_cxr_dirs)
        self.load_file_list()
        self.save_settings()

    def clear_all(self):
        self.folder_path.set("")
        self.file_list.clear()
        if not self.placeholder_label:
             self.placeholder_label = tb.Label(self.file_list_frame, text="Drag&drop .cxr files or choose folder in explorer", font=("Segoe UI", 10), style="secondary")
             self.placeholder_label.pack(pady=50)

    def on_drag_enter(self, event):
        if self.placeholder_label:
            self.placeholder_label.config(foreground="white")

    def on_drag_leave(self, event):
        if self.placeholder_label:
            self.placeholder_label.config(foreground="gray")

    def on_drop(self, event):
        self.on_drag_leave(event)
        if self.placeholder_label:
            self.placeholder_label.destroy()
            self.placeholder_label = None
        paths = self.master.tk.splitlist(event.data)
        cxr_files = [p for p in paths if p.lower().endswith(".cxr")]
        if not cxr_files:
            return

        # Add new files to the list
        for f_path in cxr_files:
            f_name = os.path.basename(f_path)
            if f_name not in [item["data"][0] for item in self.file_list.items]:
                var = tb.BooleanVar(value=True)
                cb = tb.Checkbutton(self.file_list, text=f_name, variable=var, bootstyle="info")
                self.file_list.add_item(cb, (f_name, var, f_path))

        # Set folder path from the first dropped file if not already set
        if not self.folder_path.get() and cxr_files:
            folder = os.path.dirname(cxr_files[0])
            self.folder_path.set(folder)
            if folder not in self.last_cxr_dirs:
                self.last_cxr_dirs.insert(0, folder)
                self.last_cxr_dirs = self.last_cxr_dirs[:5]
                self.folder_menu.config(values=self.last_cxr_dirs)
                self.save_settings()

    def load_file_list(self, append=False):
        if not append:
            self.file_list.clear()
            if self.placeholder_label:
                self.placeholder_label.destroy()
                self.placeholder_label = None

        folder = self.folder_path.get()
        if not folder:
            return

        cxr_files = [f for f in os.listdir(folder) if f.lower().endswith(".cxr")]
        if not cxr_files and not self.file_list.items:
             self.placeholder_label = tb.Label(self.file_list_frame, text="No .cxr files found", font=("Segoe UI", 10), style="secondary")
             self.placeholder_label.pack(pady=50)
             return

        if self.placeholder_label:
            self.placeholder_label.destroy()
            self.placeholder_label = None

        for f_name in cxr_files:
            if f_name not in [item["data"][0] for item in self.file_list.items]:
                var = tb.BooleanVar(value=True)
                f_path = os.path.join(folder, f_name)
                cb = tb.Checkbutton(self.file_list, text=f_name, variable=var, bootstyle="info-square-toggle")
                self.file_list.add_item(cb, (f_name, var, f_path))

    def toggle_all(self):
        if not self.file_list.items:
            return
        
        # Check if all items are checked
        all_checked = all(item["data"][1].get() for item in self.file_list.items)

        # Toggle the check state
        for item in self.file_list.items:
            item["data"][1].set(not all_checked)

    def start_conversion(self):
        self.save_settings()
        if not self.corona_cmd or not os.path.isfile(self.corona_cmd):
            messagebox.showerror("Error", "CoronaImageCmd.exe not selected or invalid.")
            return
        
        selected_files = [item["data"] for item in self.file_list.items if item["data"][1].get()]
        if not selected_files:
            messagebox.showinfo("No files", "No files selected for conversion.")
            return

        output_format = self.format_var.get()
        beauty_only = self.beauty_only_var.get()
        corona_cmd = self.corona_cmd
        config_path = self.config_file

        # Determine output folder
        # If a folder is selected, use it. Otherwise, use the directory of the first dropped file.
        output_dir_base = self.folder_path.get()
        if not output_dir_base and selected_files:
             output_dir_base = os.path.dirname(selected_files[0][2])
        
        if not output_dir_base:
            messagebox.showerror("Error", "Cannot determine output directory.")
            return

        output_folder = os.path.join(output_dir_base, output_format.upper())
        os.makedirs(output_folder, exist_ok=True)

        def worker():
            total = len(selected_files)
            for idx, (filename, _, input_path) in enumerate(selected_files, 1):
                name_base = os.path.splitext(filename)[0]
                output_path = os.path.join(output_folder, f"{name_base}.{output_format}")
                cmd = []
                if config_path:
                    cmd.extend(["--config", config_path])
                if beauty_only:
                    cmd.extend(["--element", "BEAUTY"])
                cmd.extend([input_path, output_path])
                try:
                    result = subprocess.run([corona_cmd] + cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"[Error] {filename}\n{result.stderr}")
                except Exception as e:
                    print(f"[Exception] {e}")
                prog = idx / total * 100
                self.master.after(0, lambda p=prog: self.progress_bar.config(value=p))
                self.master.after(0, lambda t=idx: self.status_label.config(text=f"Done {t}/{total}"))
            messagebox.showinfo("Done", f"Conversion complete!\n{len(selected_files)} files.")
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    app = TkinterDnD.Tk()
    app.title(APP_NAME)
    app.geometry("680x670")
    app.configure(bg=COLOR_BG)

    style = tb.Style("superhero")

    main_app = PinooCXRApp(app)

    def on_closing():
        main_app.save_settings()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()
