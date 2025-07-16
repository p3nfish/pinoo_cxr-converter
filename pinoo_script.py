import os
import sys
import subprocess
import threading
import configparser
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox

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
    r"C:\Program Files\Corona\CoronaImageCmd.exe"
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

class PinooCXRApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("680x670")
        self.config = PortableConfig(os.path.join(get_app_dir(), CONFIG_FILENAME))
        self.corona_cmd = None
        self.corona_cmd_dir = self.config.get("main", "corona_cmd_dir")
        self.last_cxr_dir = self.config.get("main", "last_cxr_dir")
        self.file_vars = []
        self.folder_path = ""
        self.config_file = None

        # Style/Theme
        self.root.configure(bg=COLOR_BG)
        style = tb.Style("superhero")
        style.configure('Accent.TButton', background=COLOR_ACCENT, foreground='white', font=("Segoe UI", 12, "bold"), borderwidth=0, focusthickness=1)
        style.map('Accent.TButton', background=[('active', '#13b7a7'), ('!active', COLOR_ACCENT)])
        style.configure('Danger.TButton', foreground=COLOR_DANGER, borderwidth=1)
        style.configure('Frame', background=COLOR_BG)
        style.configure('TLabel', background=COLOR_BG, foreground='white')
        style.configure('TCheckbutton', background=COLOR_BG, foreground='white')
        style.configure('TEntry', fieldbackground='#202326')
        style.configure('TLabelframe', background=COLOR_BG, foreground='white')

        self.build_gui()
        self.auto_find_corona_cmd()

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
        frm = tb.Frame(self.root, padding=10)
        frm.pack(fill=BOTH, expand=True)

        # CoronaImageCmd status line
        self.cmd_status_var = tb.StringVar()
        self.cmd_status_btn = tb.Button(frm, textvariable=self.cmd_status_var, command=self.choose_corona_cmd,
                                        style="TButton", bootstyle="secondary-outline")
        self.cmd_status_btn.pack(fill=X, pady=(0, 12))

        # File frame
        file_box = tb.Labelframe(frm, text="Found .CXR files", padding=10, bootstyle="info")
        file_box.pack(fill=BOTH, expand=True, pady=5)
        self.file_list_container = tb.Frame(file_box)
        self.file_list_container.pack(fill=BOTH, expand=True, padx=(18,0), pady=(2, 2))

        # Row with Deselect All and Choose Folder
        row = tb.Frame(frm)
        row.pack(fill=X, pady=8)
        self.deselect_btn = tb.Button(row, text="Deselect all", command=self.toggle_all, bootstyle="secondary-outline")
        self.deselect_btn.pack(side=LEFT, fill=X, expand=True, padx=(0,5))
        self.choose_folder_btn = tb.Button(row, text="Choose folder", command=self.select_folder, bootstyle="secondary-outline")
        self.choose_folder_btn.pack(side=LEFT, fill=X, expand=True, padx=(5,0))

        # Format, Beauty, Conf, stacked row
        opts_row = tb.Frame(frm)
        opts_row.pack(fill=X)
        tb.Label(opts_row, text="Format:", width=8, anchor="w").pack(side=LEFT)
        self.format_var = tb.StringVar(value="jpg")
        tb.Combobox(opts_row, textvariable=self.format_var, values=SUPPORTED_FORMATS, state="readonly", width=8).pack(side=LEFT, padx=(0, 10))

        self.beauty_only_var = tb.BooleanVar(value=True)
        tb.Checkbutton(opts_row, text="only BEAUTY", variable=self.beauty_only_var, bootstyle="success-round-toggle").pack(side=LEFT, padx=(0, 12))
        self.config_btn = tb.Button(opts_row, text="Choose .conf", command=self.select_config, bootstyle="secondary-outline")
        self.config_btn.pack(side=LEFT)

        # Progress
        self.progress_bar = tb.Progressbar(frm, orient=HORIZONTAL, length=500, mode="determinate", bootstyle="info-striped")
        self.progress_bar.pack(fill=X, pady=(12, 8))

        # Convert button (accent color)
        self.convert_btn = tb.Button(frm, text="Convert", command=self.start_conversion,
                                    bootstyle="Accent.TButton")
        self.convert_btn.pack(fill=X, pady=(0, 8), ipady=8)

        self.status_label = tb.Label(frm, text="", font=("Segoe UI", 10), anchor="w")
        self.status_label.pack(fill=X)

        # Donate
        tb.Button(frm, text="💸 Buy me a coffee", command=lambda: os.system(f'start {DONATE_LINK}'),
                  bootstyle="warning-outline").pack(fill=X, pady=(18, 0))

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
            initialdir=self.folder_path or self.last_cxr_dir or "",
            filetypes=[("Corona Config", "*.conf")]
        )
        if path:
            self.config_file = path

    def select_folder(self):
        init_dir = self.last_cxr_dir if self.last_cxr_dir and os.path.isdir(self.last_cxr_dir) else ""
        folder = filedialog.askdirectory(title="Choose folder with .cxr files", initialdir=init_dir)
        if not folder:
            return
        self.folder_path = folder
        self.config.set("main", "last_cxr_dir", folder)
        self.load_file_list()

    def load_file_list(self):
        for widget in self.file_list_container.winfo_children():
            widget.destroy()
        self.file_vars.clear()
        if not self.folder_path:
            return
        cxr_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(".cxr")]
        if not cxr_files:
            tb.Label(self.file_list_container, text="No .cxr files found", background=COLOR_BG, foreground="#bbb").pack(anchor="w")
            return
        for f in cxr_files:
            var = tb.BooleanVar(value=True)
            cb = tb.Checkbutton(self.file_list_container, text=f, variable=var, bootstyle="info-round-toggle")
            cb.pack(anchor="w", padx=10)
            self.file_vars.append((f, var))
        self.deselect_btn.config(text="Deselect all")

    def toggle_all(self):
        if not self.file_vars:
            return
        all_selected = all(var.get() for _, var in self.file_vars)
        for _, var in self.file_vars:
            var.set(not all_selected)
        self.deselect_btn.config(text="Select all" if all_selected else "Deselect all")

    def start_conversion(self):
        if not self.corona_cmd or not os.path.isfile(self.corona_cmd):
            messagebox.showerror("Error", "CoronaImageCmd.exe not selected or invalid.")
            return
        selected = [name for name, var in self.file_vars if var.get()]
        if not selected:
            messagebox.showinfo("No files", "No files selected for conversion.")
            return
        output_format = self.format_var.get()
        beauty_only = self.beauty_only_var.get()
        folder = self.folder_path
        corona_cmd = self.corona_cmd
        config_path = self.config_file
        output_folder = os.path.join(folder, output_format.upper())
        os.makedirs(output_folder, exist_ok=True)
        def worker():
            total = len(selected)
            for idx, filename in enumerate(selected, 1):
                input_path = os.path.join(folder, filename)
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
                self.root.after(0, lambda p=prog: self.progress_bar.config(value=p))
                self.root.after(0, lambda t=idx: self.status_label.config(text=f"Done {t}/{total}"))
            messagebox.showinfo("Done", f"Conversion complete!\n{len(selected)} files.")
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    app = tb.Window(themename="superhero")
    PinooCXRApp(app)
    app.mainloop()
