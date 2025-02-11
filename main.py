
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext, messagebox, filedialog, colorchooser, Listbox, EXTENDED, Button, Frame, Canvas
import time
import threading
import os
import uuid
from collections import deque
from PIL import Image, ImageTk
from datetime import datetime
import socket
import webbrowser
import subprocess
import tornado.ioloop
import tornado.web
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


# ... (Projekt 1 - Process, File, FileSystem, Scheduler classes - bez zmian) ...
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

class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WhiteWar")
        self.root.geometry("1200x600")

        # Current directory
        self.current_directory = os.path.join(os.getcwd(), "img")  # Default to img directory

        # Default image path
        self.default_image_path = os.path.join(os.getcwd(), "img\\ikigai.jpeg")

        # Create a default image if it doesn't exist
        self.create_default_image()

        # GUI Layout
        self.setup_gui()
        self.populate_tree(self.current_directory, "") #populate tree on startup

    def create_default_image(self):
        if not os.path.exists(self.default_image_path):
            img = Image.new('RGB', (800, 600), color='gray')
            img.save(self.default_image_path)

    def setup_gui(self):
        # File and folder tree
        self.tree = ttk.Treeview(self.root, show="tree", height=20, selectmode=tk.BROWSE)
        self.tree.pack(side="left", fill="y", padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Image display area
        self.image_frame = Frame(self.root)
        self.image_frame.pack(side="right", fill="both", expand=True)

        self.canvas = Canvas(self.image_frame, bg="white")
        self.canvas.pack(fill="both", expand=True)

         # Text display area
        self.text_area = scrolledtext.ScrolledText(self.image_frame, wrap=tk.WORD, width=80, height=25)
        self.text_area.pack(fill="both", expand=True)
        self.text_area.pack_forget() # hide text area at start

        # Buttons
        self.button_frame = Frame(self.root)
        self.button_frame.pack(side="bottom", fill="x")

        Button(self.button_frame, text="Previous Image", command=self.prev_image).pack(side="top")
        Button(self.button_frame, text="Next Image", command=self.next_image).pack(side="top")
        Button(self.button_frame, text="New File", command=self.create_new_file).pack(side="top")


        self.show_default_image()

    def populate_tree(self, parent_dir, parent_id):
        try:
            for item in os.listdir(parent_dir):
                item_path = os.path.join(parent_dir, item)
                item_id = self.tree.insert(parent_id, 'end', text=item, open=False)

                if os.path.isdir(item_path):
                    self.populate_tree(item_path, item_id)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Directory not found: {parent_dir}")


    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            item_id = selected_items[0]
            item_path = self.get_path_from_tree_item(item_id)

            if os.path.isfile(item_path):
                self.show_file_content(item_path) # Show content for files
            else:
                self.show_default_image()

    def get_path_from_tree_item(self, item_id):
        path = self.tree.item(item_id, 'text')
        parent_id = self.tree.parent(item_id)

        while parent_id:
            path = os.path.join(self.tree.item(parent_id, 'text'), path)
            parent_id = self.tree.parent(parent_id)

        return os.path.join(self.current_directory,path)

    def is_image_file(self, path):
        image_extensions = (".png", ".jpg", ".jpeg", ".gif")
        return path.lower().endswith(image_extensions)

    def is_text_file(self,path):
      text_extensions = (".txt", ".log", ".py")
      return path.lower().endswith(text_extensions)

    def show_file_content(self, file_path):
        self.text_area.pack_forget()
        self.canvas.pack_forget()

        if self.is_image_file(file_path):
            self.show_image(file_path)
            self.canvas.pack(fill="both", expand=True)
        elif self.is_text_file(file_path):
            self.show_text_content(file_path)
            self.text_area.pack(fill="both", expand=True)
        else:
            self.open_selected_file(file_path) #open with default application
            self.show_default_image()

    def show_image(self, image_path):
         try:
            if image_path:
                self.text_area.pack_forget()
                self.canvas.pack(fill="both", expand=True)
                img = Image.open(image_path)
                img.thumbnail((800, 600))
                photo = ImageTk.PhotoImage(img)
                self.canvas.delete("all")
                self.canvas.create_image(400, 300, image=photo, anchor="center")
                self.canvas.image = photo
         except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            self.show_default_image()

    def show_text_content(self, file_path):
       try:
           self.canvas.pack_forget()
           self.text_area.pack(fill="both", expand=True)
           with open(file_path, 'r', encoding='utf-8') as file:
               content = file.read()
               self.text_area.delete('1.0', tk.END)
               self.text_area.insert('1.0', content)
       except Exception as e:
            self.text_area.delete('1.0', tk.END)
            self.text_area.insert('1.0', f"Error reading file: {e}")

    def show_default_image(self):
        img = Image.open(self.default_image_path)
        photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(400, 300, image=photo, anchor="center")
        self.canvas.image = photo
        self.text_area.pack_forget()

    def prev_image(self):
        # Not needed in current approach
        pass

    def next_image(self):
        # Not needed in current approach
        pass

    def create_new_file(self):
        # Not needed in current approach
        pass

    def open_selected_file(self, file_path):
        try:
            if file_path:
                subprocess.Popen(['start', file_path], shell=True)  # Windows
            else:
                messagebox.showerror("Error", f"No file selected")
        except FileNotFoundError:
                messagebox.showerror("Error", f"File not found: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open the file: {e}")


class OS:
    def __init__(self, root):
        # ... (Projekt 1 - OS.__init__ - większość bez zmian)
        self.create_icons()  # Ważne: Wywołujemy po self.create_desktop()
        self.update_time()

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

        # Dodajemy wątek Tornado
        self.tornado_thread = threading.Thread(target=self.run_tornado, daemon=True)
        self.tornado_thread.start()
        self.SERVER_URL = "http://localhost:8888/search"
        # Dodajemy wątek Tornado z obsługą wyjątków i możliwością ponownego uruchomienia
        self.tornado_thread = None
        self.start_tornado_server()


    # ... (Projekt 1 - OS - metody bez zmian: create_desktop, create_taskbar, update_time, open_file_manager, create_file_manager_widgets, update_file_list, create_example_file, create_new_file, open_selected_file, show_file_content, delete_selected_file, open_settings, create_settings_widgets, create_network_settings, update_ip_address, update_hostname, create_personalization_settings, choose_background_color, add_taskbar_button, handle_taskbar_button_click, handle_window_state, handle_window_destroy) ...
    def create_desktop(self):
        self.desktop = tk.Frame(self.root, bg=self.desktop_bg_color)
        self.desktop.pack(fill=tk.BOTH, expand=True)

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
            # {"name": "File Manager", "icon": os.path.join(os.getcwd(), "img\\file_icon.png"),
            # "action": self.open_file_manager},
            {"name": "Settings", "icon": os.path.join(os.getcwd(), "img\\sys\\settings_icon.png"),
             "action": self.open_settings},
            {"name": "WitchCraft", "icon": os.path.join(os.getcwd(), "img\\sys\\musical-note.png"),
             "action": self.open_yii_app},
            {"name": "White War", "icon": os.path.join(os.getcwd(), "img\\sys\\file_icon.png"),
             "action": self.open_image_viewer},
            {"name": "Stock Analyzer", "icon": os.path.join(os.getcwd(), "img\\sys\\chart_icon.png"),
             "action": self.open_stock_analyzer},  # Nowa ikona
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
            except Exception as e:
                print(f"Wystąpił błąd: {e}")

    def update_time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        #self.time_label.config(text=current_time)
        #self.root.after(1000, self.update_time)

    def open_yii_app(self):
        try:
            # Podmień "192.168.1.100" na adres IP serwera, na którym jest Yii
            webbrowser.open("yii-application.test")
        except webbrowser.Error as e:
            messagebox.showerror("Error", f"Nie można otworzyć przeglądarki: {e}")

    def open_image_viewer(self):
        if "image_viewer" not in self.app_windows or not self.app_windows["image_viewer"].winfo_exists():
            image_viewer_window = tk.Toplevel(self.root)
            self.app_windows["image_viewer"] = image_viewer_window
            ImageViewerApp(image_viewer_window)
            self.add_taskbar_button("image_viewer", "Image Viewer", image_viewer_window)
        else:
            self.app_windows["image_viewer"].lift()

    def open_stock_analyzer(self):
        if "stock_analyzer" not in self.app_windows or not self.app_windows["stock_analyzer"].winfo_exists():
            stock_analyzer_window = tk.Toplevel(self.root)
            stock_analyzer_window.title("Stock Analyzer")
            self.app_windows["stock_analyzer"] = stock_analyzer_window
            self.create_stock_analyzer_widgets(stock_analyzer_window)
            self.add_taskbar_button("stock_analyzer", "Stock Analyzer", stock_analyzer_window)
        else:
            self.app_windows["stock_analyzer"].lift()

    def create_stock_analyzer_widgets(self, parent):
        tk.Label(parent, text="Stock Symbol:").pack()
        self.stock_entry = tk.Entry(parent, width=20)
        self.stock_entry.pack()

        search_button = tk.Button(parent, text="Search", command=self.search_stock)
        search_button.pack()

        self.result_box = scrolledtext.ScrolledText(parent, width=60, height=5)
        self.result_box.pack()

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

    def search_stock(self):
        symbol = self.stock_entry.get()

        try:
            response = requests.post(self.SERVER_URL, json={"symbol": symbol})
            data = response.json()

            if "message" in data:
                self.result_box.delete(1.0, tk.END)
                self.result_box.insert(tk.END, f"Data saved: {symbol}_history.csv")
                self.show_plot(f"{symbol}_history.csv")
            else:
                self.result_box.delete(1.0, tk.END)
                self.result_box.insert(tk.END, "Error: " + data.get("error", "Unknown error"))
        except Exception as e:
            messagebox.showerror("Error", f"Could not connect to server: {e}")

    def show_plot(self, file_path):
        try:
            df = pd.read_csv(file_path)
            df["Close"] = pd.to_numeric(df["Close"], errors='coerce')
            df["Date"] = pd.to_datetime(df["Date"])

            plt.figure(figsize=(10, 5))
            plt.plot(df["Date"], df["Close"], marker='o', linestyle='-')
            plt.xlabel("Date")
            plt.ylabel("Closing Price")
            plt.title("Stock Price Chart")
            plt.xticks(rotation=45)
            plt.grid()
            plt.show()
        except Exception as e:
            messagebox.showerror("Error", f"Could not display plot: {e}")

    def start_tornado_server(self):
        if self.tornado_thread is None or not self.tornado_thread.is_alive():
            self.tornado_thread = threading.Thread(target=self.run_tornado, daemon=True)
            self.tornado_thread.start()
            self.SERVER_URL = "http://localhost:8888/search"
        else:
            print("Serwer Tornado już działa.")

    def stop_tornado_server(self):
        if self.tornado_thread and self.tornado_thread.is_alive():
            tornado.ioloop.IOLoop.current().add_callback(tornado.ioloop.IOLoop.current().stop)
            self.tornado_thread.join()
            self.tornado_thread = None
            print("Serwer Tornado zatrzymany.")
        else:
            print("Serwer Tornado nie jest uruchomiony.")

    def run_tornado(self):
        try:
            app = tornado.web.Application([(r"/search", StockSearchHandler)])
            app.listen(8888)  # Można zmienić port, np. na 8889, jeśli 8888 jest zajęty
            print("✅ Tornado server running on http://localhost:8888")
            tornado.ioloop.IOLoop.current().start()
        except OSError as e:
            if e.errno == 10048:  # Port jest zajęty
                print("❌ Port 8888 jest zajęty. Spróbuj innego portu.")
                # Opcjonalnie: Można spróbować automatycznie znaleźć wolny port
            else:
                print(f"❌ Błąd serwera Tornado: {e}")
        except Exception as e:
            print(f"❌ Nieznany błąd serwera Tornado: {e}")


# ... (Projekt 1 - funkcje example_process i warunek if __name__ == "__main__" - bez zmian) ...

# Backend Tornado API (bez zmian, umieszczamy poza klasą OS)
class StockSearchHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        stock_symbol = data.get("symbol")

        if not stock_symbol:
            self.write({"error": "Brak symbolu giełdowego."})
            return

        url = f"https://finance.yahoo.com/quote/{stock_symbol}/history?p={stock_symbol}"

        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr")

            history = []
            for row in rows[1:]:  # Pomijamy nagłówek
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue
                history.append([
                    cols[0].text,  # Data
                    cols[1].text,  # Open
                    cols[2].text,  # High
                    cols[3].text,  # Low
                    cols[4].text,  # Close
                    cols[5].text  # Volume
                ])

            df = pd.DataFrame(history, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            df.to_csv(f"{stock_symbol}_history.csv", index=False)

            self.write({"message": "Dane zapisane", "path": f"{stock_symbol}_history.csv"})
        except Exception as e:
            self.write({"error": str(e)})


# Uruchamianie Tornado w osobnym wątku
def run_tornado():
    app = tornado.web.Application([(r"/search", StockSearchHandler)])
    app.listen(8888)
    print("✅ Serwer Tornado działa na http://localhost:8888")
    tornado.ioloop.IOLoop.current().start()


tornado_thread = threading.Thread(target=run_tornado, daemon=True)
tornado_thread.start()

# GUI Tkinter
SERVER_URL = "http://localhost:8888/search"


def search_stock():
    symbol = stock_entry.get()

    try:
        response = requests.post(SERVER_URL, json={"symbol": symbol})
        data = response.json()

        if "message" in data:
            result_box.delete(1.0, tk.END)
            result_box.insert(tk.END, f"Dane zapisane: {symbol}_history.csv")
            show_plot(f"{symbol}_history.csv")
        else:
            result_box.delete(1.0, tk.END)
            result_box.insert(tk.END, "Błąd: " + data.get("error", "Nieznany błąd"))
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie można połączyć się z serwerem: {e}")


def show_plot(file_path):
    try:
        df = pd.read_csv(file_path)
        df["Close"] = pd.to_numeric(df["Close"], errors='coerce')
        df["Date"] = pd.to_datetime(df["Date"])

        plt.figure(figsize=(10, 5))
        plt.plot(df["Date"], df["Close"], marker='o', linestyle='-')
        plt.xlabel("Data")
        plt.ylabel("Cena zamknięcia")
        plt.title("Wykres cen akcji")
        plt.xticks(rotation=45)
        plt.grid()
        plt.show()
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie można wyświetlić wykresu: {e}")

if __name__ == "__main__":
    root = tk.Tk()  # Tworzymy główne okno Tkinter
    root.title("WW Space")
    root.geometry("800x600")
    my_os = OS(root)  # Tworzymy instancję OS i przekazujemy jej root

    # Ważne: Zamykamy wątek Tornado przy zamykaniu aplikacji Tkinter
    root.protocol("WM_DELETE_WINDOW", lambda: [tornado.ioloop.IOLoop.current().stop(), root.destroy()])
    root.mainloop()  # Uruchamiamy pętlę główną Tkinter
