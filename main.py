import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext, messagebox, filedialog, colorchooser
import time
import threading
import os
import uuid
from collections import deque
from PIL import Image, ImageTk
from datetime import datetime
import socket


class Process:
    def __init__(self, target, args=(), name=None, is_daemon=False):
        self.id = uuid.uuid4()
        self.target = target
        self.args = args
        self.name = name if name else f"Process-{self.id}"
        self.is_daemon = is_daemon
        self.thread = None
        self.status = "waiting"  # "waiting", "running", "stopped"
        self.output = []

    def start(self):
        if self.status == "waiting":
            self.status = "running"
            self.thread = threading.Thread(target=self._run, daemon=self.is_daemon)
            self.thread.start()

    def _run(self):
        try:
            result = self.target(*self.args)
            self.output.append(result)
        except Exception as e:
            self.output.append(f"Error: {e}")
        finally:
            self.status = "stopped"

    def stop(self):
        if self.thread and self.status == "running":
            self.status = "stopped"
            # W tym uproszczonym modelu nie zabijamy wątku, ale to można rozbudować.
            self.thread.join()

    def join(self):
        if self.thread and self.status != "stopped":
            self.thread.join()


class File:
    def __init__(self, name):
        self.name = name
        self.content = ""


class FileSystem:
    def __init__(self):
        self.files = {}

    def create_file(self, name):
        if name not in self.files:
            self.files[name] = File(name)
            return True
        return False

    def read_file(self, name):
        if name in self.files:
            return self.files[name].content
        return None

    def write_file(self, name, content):
        if name in self.files:
            self.files[name].content = content
            return True
        return False

    def delete_file(self, name):
        if name in self.files:
            del self.files[name]
            return True
        return False


class Scheduler:
    def __init__(self):
        self.tasks = deque()
        self._run = True
        self._thread = threading.Thread(target=self._schedule)
        self._thread.start()

    def add_task(self, process, interval):
        self.tasks.append((process, interval, time.time()))

    def _schedule(self):
        while self._run:
            if self.tasks:
                process, interval, last_run = self.tasks.popleft()
                if time.time() - last_run >= interval:
                    process.start()
                    self.tasks.append((process, interval, time.time()))
                else:
                    self.tasks.appendleft((process, interval, last_run))
            time.sleep(0.1)

    def stop(self):
        self._run = False
        self._thread.join()


class OS:
    def __init__(self, root):
        self.root = root
        self.processes = {}
        self.filesystem = FileSystem()
        self.scheduler = Scheduler()
        self.app_windows = {}
        self.taskbar_buttons = {}
        self.desktop_bg_color = "lightgray"
        self.create_desktop()
        self.create_taskbar()
        self.create_icons()
        self.update_time()

    def create_process(self, target, args=(), name=None, is_daemon=False):
        process = Process(target, args, name, is_daemon)
        self.processes[process.id] = process
        return process

    def get_process(self, process_id):
        return self.processes.get(process_id)

    def start_process(self, process_id):
        process = self.processes.get(process_id)
        if process:
            process.start()

    def stop_process(self, process_id):
        process = self.processes.get(process_id)
        if process:
            process.stop()

    def create_file(self, name):
        return self.filesystem.create_file(name)

    def read_file(self, name):
        return self.filesystem.read_file(name)

    def write_file(self, name, content):
        return self.filesystem.write_file(name, content)

    def delete_file(self, name):
        return self.filesystem.delete_file(name)

    def schedule_task(self, process, interval):
        self.scheduler.add_task(process, interval)

    def stop_scheduler(self):
        self.scheduler.stop()

    def create_desktop(self):
        self.desktop = tk.Frame(self.root, bg=self.desktop_bg_color)
        self.desktop.pack(fill=tk.BOTH, expand=True)

    def create_taskbar(self):
        self.taskbar = tk.Frame(self.root, bg="gray")
        self.taskbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Start menu button
        self.start_menu_button = tk.Menubutton(self.taskbar, text="Start", relief=tk.RAISED,
                                               borderwidth=2, bg="lightgray")
        self.start_menu_button.pack(side=tk.LEFT, padx=5, pady=2)
        self.start_menu = tk.Menu(self.start_menu_button, tearoff=0)
        self.start_menu_button["menu"] = self.start_menu

        # Task buttons area
        self.task_button_area = tk.Frame(self.taskbar, bg="gray")
        self.task_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Time Label
        self.time_label = tk.Label(self.taskbar, text="", bg="gray", fg="white")
        self.time_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def create_icons(self):
        icons_data = [
            {"name": "File Manager", "icon": "file_icon.png", "action": self.open_file_manager},
            {"name": "Settings", "icon": "settings_icon.png", "action": self.open_settings},
        ]

        for i, icon_data in enumerate(icons_data):
            try:
                image = Image.open(icon_data["icon"]).resize((64, 64))
                photo = ImageTk.PhotoImage(image)
                label = tk.Label(self.desktop, image=photo, text=icon_data["name"], compound=tk.TOP,
                                 bg=self.desktop_bg_color, cursor="hand2")
                label.image = photo  # Zachowaj referencję
                label.grid(row=i // 2, column=i % 2, padx=20, pady=20)
                label.bind("<Button-1>", lambda event, action=icon_data["action"]: action())

                # Add to start menu
                self.start_menu.add_command(label=icon_data["name"], command=icon_data["action"])

            except FileNotFoundError:
                print(f"Brak pliku: {icon_data['icon']}")

    def update_time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)

    def open_file_manager(self):
        if "file_manager" not in self.app_windows or not self.app_windows["file_manager"].winfo_exists():
            file_manager_window = tk.Toplevel(self.root)
            file_manager_window.title("File Manager")
            self.app_windows["file_manager"] = file_manager_window
            self.create_file_manager_widgets(file_manager_window)
            self.add_taskbar_button("file_manager", "File Manager", file_manager_window)
        else:
            self.app_windows["file_manager"].lift()

    def create_file_manager_widgets(self, parent):
        # File listbox
        file_frame = ttk.LabelFrame(parent, text="File List")
        file_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.file_listbox = tk.Listbox(file_frame, width=50)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.update_file_list()

        # File operations
        operation_frame = ttk.LabelFrame(parent, text="Operations")
        operation_frame.pack(padx=10, pady=10, fill=tk.X)
        ttk.Button(operation_frame, text="Create File", command=self.create_new_file).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(operation_frame, text="Open File", command=self.open_selected_file).pack(side=tk.LEFT, padx=5,
                                                                                            pady=5)
        ttk.Button(operation_frame, text="Delete File", command=self.delete_selected_file).pack(side=tk.LEFT, padx=5,
                                                                                                pady=5)
        ttk.Button(operation_frame, text="Create Example File", command=self.create_example_file).pack(side=tk.LEFT,
                                                                                                       padx=5, pady=5)

        self.file_name_entry = ttk.Entry(operation_frame, width=20)
        self.file_name_entry.pack(side=tk.LEFT, padx=5, pady=5)

    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for file_name in self.filesystem.files.keys():
            self.file_listbox.insert(tk.END, file_name)

    def create_example_file(self):
        name = "example.txt"
        if self.create_file(name):
            self.write_file(name, "This is an example file created from button in file manager.")
            self.update_file_list()
            messagebox.showinfo("Success", f"File '{name}' created")
        else:
            messagebox.showerror("Error", f"File '{name}' already exists")

    def create_new_file(self):
        name = self.file_name_entry.get()
        if name:
            if self.create_file(name):
                self.update_file_list()
                messagebox.showinfo("Success", f"File '{name}' created")
            else:
                messagebox.showerror("Error", f"File '{name}' already exists")
        else:
            messagebox.showerror("Error", "File name cannot be empty")

    def open_selected_file(self):
        selected_item = self.file_listbox.curselection()
        if selected_item:
            file_name = self.file_listbox.get(selected_item[0])
            content = self.read_file(file_name)
            if content:
                self.show_file_content(file_name, content)
            else:
                messagebox.showerror("Error", f"File '{file_name}' is empty.")

    def show_file_content(self, file_name, content):
        if file_name not in self.app_windows or not self.app_windows[file_name].winfo_exists():
            file_window = tk.Toplevel(self.root)
            file_window.title(f"File Content: {file_name}")
            text_area = scrolledtext.ScrolledText(file_window, width=50, height=20)
            text_area.insert(tk.END, content)
            text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            self.app_windows[file_name] = file_window
            self.add_taskbar_button(file_name, f"File: {file_name}", file_window)
        else:
            self.app_windows[file_name].lift()

    def delete_selected_file(self):
        selected_item = self.file_listbox.curselection()
        if selected_item:
            file_name = self.file_listbox.get(selected_item[0])
            if self.delete_file(file_name):
                self.update_file_list()
                messagebox.showinfo("Success", f"File '{file_name}' deleted")
            else:
                messagebox.showerror("Error", f"File '{file_name}' not found")
        else:
            messagebox.showerror("Error", f"No file is selected")

    def open_settings(self):
        if "settings" not in self.app_windows or not self.app_windows["settings"].winfo_exists():
            settings_window = tk.Toplevel(self.root)
            settings_window.title("Settings")
            self.app_windows["settings"] = settings_window
            self.create_settings_widgets(settings_window)
            self.add_taskbar_button("settings", "Settings", settings_window)
        else:
            self.app_windows["settings"].lift()

    def create_settings_widgets(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.create_network_settings(notebook)
        self.create_personalization_settings(notebook)

    def create_network_settings(self, notebook):
        network_frame = ttk.Frame(notebook)
        notebook.add(network_frame, text="Network")

        ip_label = ttk.Label(network_frame, text="IP Address:")
        ip_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.ip_display = ttk.Label(network_frame, text="Not Available")
        self.ip_display.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.update_ip_address()

        hostname_label = ttk.Label(network_frame, text="Hostname:")
        hostname_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.hostname_display = ttk.Label(network_frame, text="Not Available")
        self.hostname_display.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.update_hostname()

        refresh_button = ttk.Button(network_frame, text="Refresh",
                                    command=lambda: [self.update_ip_address(), self.update_hostname()])
        refresh_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

    def update_ip_address(self):
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            self.ip_display.config(text=ip_address)
        except socket.gaierror:
            self.ip_display.config(text="Not Available")
        except Exception as e:
            self.ip_display.config(text="Error")
            print(f"Error in update_ip_address: {e}")

    def update_hostname(self):
        try:
            hostname = socket.gethostname()
            self.hostname_display.config(text=hostname)
        except socket.gaierror:
            self.hostname_display.config(text="Not Available")
        except Exception as e:
            self.hostname_display.config(text="Error")
            print(f"Error in update_hostname: {e}")

    def create_personalization_settings(self, notebook):
        personalization_frame = ttk.Frame(notebook)
        notebook.add(personalization_frame, text="Personalization")

        bg_color_label = ttk.Label(personalization_frame, text="Desktop Background Color:")
        bg_color_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        bg_color_button = ttk.Button(personalization_frame, text="Choose Color", command=self.choose_background_color)
        bg_color_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

    def choose_background_color(self):
        color = colorchooser.askcolor(title="Choose Background Color")[1]
        if color:
            self.desktop_bg_color = color
            self.desktop.config(bg=self.desktop_bg_color)
            for label in self.desktop.winfo_children():
                if isinstance(label, tk.Label):
                    label.config(bg=self.desktop_bg_color)

    def add_taskbar_button(self, app_key, app_name, window):
        button = ttk.Button(self.task_button_area, text=app_name,
                            command=lambda win=window: self.handle_taskbar_button_click(win))
        button.pack(side=tk.LEFT, padx=2, pady=2)
        self.taskbar_buttons[app_key] = button

        def on_close():
            button.destroy()
            del self.taskbar_buttons[app_key]

            if app_key in self.app_windows:
                self.app_windows[app_key].destroy()
                del self.app_windows[app_key]

        window.protocol("WM_DELETE_WINDOW", on_close)
        window.protocol("WM_STATE", lambda event, win=window: self.handle_window_state(win, event))

        window.bind("<Destroy>", lambda event, win=window: self.handle_window_destroy(win))

    def handle_window_destroy(self, window):
        for key, app_window in self.app_windows.items():
            if app_window == window:
                del self.app_windows[key]
                print(f"Window destroyed: {key}")
                break

    def handle_taskbar_button_click(self, window):
        if window.winfo_state() == 'normal':
            window.withdraw()
        else:
            window.deiconify()
            window.lift()

    def handle_window_state(self, window, event):
        if event.type == "22":  # WM_STATE event
            if window.winfo_state() == "withdrawn":
                print("zminimalizowane")
            elif window.winfo_state() == "normal":
                print("normalne")
            elif window.winfo_state() == "iconic":
                print("zminimalizowane")


def example_process(name, delay):
    print(f"Process {name} is starting")
    time.sleep(delay)
    print(f"Process {name} is finishing")
    return f"Process {name} completed after {delay} seconds."


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Mini OS")
    root.geometry("800x600")
    my_os = OS(root)

    root.protocol("WM_DELETE_WINDOW", lambda: my_os.stop_scheduler() or root.destroy())
    root.mainloop()