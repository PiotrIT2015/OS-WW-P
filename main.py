
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
import mysql.connector
from textblob import TextBlob
import numpy as np
from scipy import linalg

# --- Konfiguracja i funkcje pomocnicze (przeniesione do zasięgu globalnego) ---

# Konfiguracja MySQL
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "search_db"
}

def setup_db():
    """Tworzy tabelę w MySQL, jeśli nie istnieje."""
    try:
        conn = mysql.connector.connect(**db_config, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            url TEXT,
            query TEXT,
            result TEXT,
            sentiment TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Baza danych MySQL jest gotowa.")
    except mysql.connector.Error as err:
        print(f"❌ Błąd połączenia z bazą danych: {err}")
        print("UWAGA: Aplikacja White Dwarf Search nie będzie zapisywać wyników.")

def analyze_sentiment(text):
    """Analiza sentymentu (proste AI)."""
    score = TextBlob(text).sentiment.polarity
    if score > 0.1:
        return "😊 Pozytywne"
    elif score < -0.1:
        return "😞 Negatywne"
    else:
        return "😐 Neutralne"

def PCA(lista, l_com):
    """Analiza PCA (Principal Component Analysis) - obecnie nieużywana w kodzie."""
    D_T = np.transpose(lista)
    Z = D_T.dot(lista)
    D, V = linalg.eig(Z)
    D2 = np.real(D)
    # Uniknięcie błędu logarytmu z zera lub liczby ujemnej
    D3 = np.log(D2, where=D2 > 0, out=np.full_like(D2, -np.inf))

    sa = V.shape
    print(f"Wymiary macierzy V: {sa}, liczba komponentów: {l_com}")

    if l_com >= sa[1]:
        C = V
    else:
        C = V[:, 0:l_com]

    print(f"Macierz transformacji C:\n{C}")
    R = lista.dot(C)
    E = np.transpose(C)
    Drep = R.dot(E)
    return Drep

# --- Backend Tornado API ---

class StockSearchHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = json.loads(self.request.body)
            stock_symbol = data.get("symbol")

            if not stock_symbol:
                self.set_status(400)
                self.write({"error": "Brak symbolu giełdowego."})
                return

            url = f"https://finance.yahoo.com/quote/{stock_symbol}/history?p={stock_symbol}"
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()  # Rzuci wyjątkiem dla kodów błędu HTTP

            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr", class_="BdT Bdc($seperatorColor)")

            history = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 6:
                    history.append([
                        cols[0].text, cols[1].text, cols[2].text,
                        cols[3].text, cols[4].text, cols[5].text
                    ])

            if not history:
                self.set_status(404)
                self.write({"error": f"Nie znaleziono danych dla symbolu '{stock_symbol}'."})
                return

            df = pd.DataFrame(history, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            file_path = f"{stock_symbol}_history.csv"
            df.to_csv(file_path, index=False)

            self.write({"message": "Dane zapisane", "path": file_path})
        except requests.exceptions.HTTPError as e:
            self.set_status(e.response.status_code)
            self.write({"error": f"Błąd HTTP podczas pobierania danych: {e}"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": f"Wystąpił wewnętrzny błąd serwera: {str(e)}"})

class WebSearchHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = json.loads(self.request.body)
            url = data.get("url")
            query = data.get("query")

            if not url or not query:
                self.set_status(400)
                self.write({"error": "URL i fraza wyszukiwania są wymagane."})
                return

            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = "\n\n".join([p.text for p in soup.find_all("p") if query.lower() in p.text.lower()])

            if not results:
                results = "Brak wyników dla podanej frazy."

            sentiment = analyze_sentiment(results)

            # Zapis do bazy, z obsługą błędów
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO search_results (url, query, result, sentiment) VALUES (%s, %s, %s, %s)",
                               (url, query, results, sentiment))
                conn.commit()
                cursor.close()
                conn.close()
            except mysql.connector.Error as db_err:
                print(f"Błąd zapisu do bazy danych: {db_err}")


            self.write({"results": results, "sentiment": sentiment})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


# --- Symulacja OS - klasy bazowe ---

class Process:
    def __init__(self, target, args=(), name=None, is_daemon=False):
        self.id = uuid.uuid4()
        self.target = target
        self.args = args
        self.name = name if name else f"Process-{self.id}"
        self.is_daemon = is_daemon
        self.thread = None
        self.status = "waiting"
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
        self._thread = threading.Thread(target=self._schedule, daemon=True)
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


# --- Aplikacje GUI ---

class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WhiteWar")
        self.root.geometry("1200x600")

        self.img_dir = "img"
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)
            
        self.current_directory = os.path.join(os.getcwd(), self.img_dir)
        self.default_image_path = os.path.join(self.current_directory, "ikigai.jpeg")

        self.create_default_image()
        self.setup_gui()
        self.populate_tree(self.current_directory, "")

    def create_default_image(self):
        if not os.path.exists(self.default_image_path):
            try:
                img = Image.new('RGB', (800, 600), color='gray')
                img.save(self.default_image_path)
            except Exception as e:
                print(f"Nie udało się stworzyć domyślnego obrazka: {e}")

    def setup_gui(self):
        main_frame = Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(main_frame, show="tree", selectmode=tk.BROWSE)
        self.tree.pack(side="left", fill="y", padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        ysb = ttk.Scrollbar(main_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.pack(side='left', fill='y')

        display_frame = Frame(main_frame, bg="black")
        display_frame.pack(side="right", fill="both", expand=True)

        self.canvas = Canvas(display_frame, bg="white")
        self.text_area = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, width=80, height=25)
        
        self.show_default_image()

    def populate_tree(self, parent_dir, parent_id):
        try:
            for item in sorted(os.listdir(parent_dir)):
                item_path = os.path.join(parent_dir, item)
                item_id = self.tree.insert(parent_id, 'end', text=item, open=False)
                if os.path.isdir(item_path):
                    self.populate_tree(item_path, item_id)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Directory not found: {parent_dir}")
        except Exception as e:
            print(f"Błąd podczas populacji drzewa: {e}")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            item_id = selected_items[0]
            item_path = self.get_path_from_tree_item(item_id)
            if os.path.isfile(item_path):
                self.show_file_content(item_path)
            else: # It's a directory
                self.show_default_image()

    def get_path_from_tree_item(self, item_id):
        path_parts = [self.tree.item(item_id, 'text')]
        parent_id = self.tree.parent(item_id)
        while parent_id:
            path_parts.insert(0, self.tree.item(parent_id, 'text'))
            parent_id = self.tree.parent(parent_id)
        return os.path.join(self.current_directory, *path_parts)

    def is_image_file(self, path):
        return path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp"))

    def is_text_file(self, path):
        return path.lower().endswith((".txt", ".log", ".py", ".md", ".json"))

    def show_file_content(self, file_path):
        if self.is_image_file(file_path):
            self.show_image(file_path)
        elif self.is_text_file(file_path):
            self.show_text_content(file_path)
        else:
            self.open_with_default_app(file_path)
            self.show_default_image()

    def show_image(self, image_path):
        try:
            self.text_area.pack_forget()
            self.canvas.pack(fill="both", expand=True)
            
            img = Image.open(image_path)
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width < 2 or canvas_height < 2: # handle initial zero size
                 canvas_width, canvas_height = 800, 600

            img.thumbnail((canvas_width, canvas_height))
            
            photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width/2, canvas_height/2, image=photo, anchor="center")
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
        self.text_area.pack_forget()
        self.canvas.pack(fill="both", expand=True)
        self.show_image(self.default_image_path)

    def open_with_default_app(self, file_path):
        try:
            if os.name == 'nt': # Windows
                os.startfile(file_path)
            elif os.name == 'posix': # macOS, Linux
                subprocess.call(('open', file_path) if sys.platform == 'darwin' else ('xdg-open', file_path))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open the file: {e}")

# --- Główna klasa systemu operacyjnego ---

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

        self.tornado_thread = None
        self.start_tornado_server()

    def create_desktop(self):
        self.desktop = tk.Frame(self.root, bg=self.desktop_bg_color)
        self.desktop.pack(fill=tk.BOTH, expand=True)

    def create_taskbar(self):
        self.taskbar = tk.Frame(self.root, bg="gray", height=30)
        self.taskbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.taskbar.pack_propagate(False) # Prevent resizing

        self.start_menu_button = tk.Menubutton(self.taskbar, text="Start", relief=tk.RAISED, borderwidth=2, bg="lightgray")
        self.start_menu_button.pack(side=tk.LEFT, padx=5, pady=2)
        self.start_menu = tk.Menu(self.start_menu_button, tearoff=0)
        self.start_menu_button["menu"] = self.start_menu

        self.task_button_area = tk.Frame(self.taskbar, bg="gray")
        self.task_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.time_label = tk.Label(self.taskbar, text="", bg="gray", fg="white")
        self.time_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def update_time(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)

    def create_icons(self):
        sys_img_dir = os.path.join(os.getcwd(), "img", "sys")
        if not os.path.exists(sys_img_dir):
            os.makedirs(sys_img_dir)
            
        icons_data = [
            {"name": "File Manager (Sim)", "icon": os.path.join(sys_img_dir, "file_icon.png"), "action": self.open_file_manager},
            {"name": "White War Explorer", "icon": os.path.join(sys_img_dir, "folder_icon.png"), "action": self.open_image_viewer},
            {"name": "Stock Analyzer", "icon": os.path.join(sys_img_dir, "chart_icon.png"), "action": self.open_stock_analyzer},
            {"name": "White Dwarf Search", "icon": os.path.join(sys_img_dir, "browser.png"), "action": self.open_white_dwarf},
            {"name": "WitchCraft (Web)", "icon": os.path.join(sys_img_dir, "musical-note.png"), "action": self.open_yii_app},
            {"name": "Settings", "icon": os.path.join(sys_img_dir, "settings_icon.png"), "action": self.open_settings},
        ]
        
        for i, icon_data in enumerate(icons_data):
            try:
                # Create a placeholder if icon file not found
                if not os.path.exists(icon_data["icon"]):
                    placeholder = Image.new('RGB', (64, 64), color='blue')
                    placeholder.save(icon_data["icon"])

                image = Image.open(icon_data["icon"]).resize((48, 48))
                photo = ImageTk.PhotoImage(image)
                label = tk.Label(self.desktop, image=photo, text=icon_data["name"], compound=tk.TOP, bg=self.desktop_bg_color, cursor="hand2", fg="white")
                label.image = photo
                label.grid(row=i // 8, column=i % 8, padx=15, pady=15)
                label.bind("<Double-1>", lambda event, action=icon_data["action"]: action())
                self.start_menu.add_command(label=icon_data["name"], command=icon_data["action"])
            except Exception as e:
                print(f"Błąd podczas tworzenia ikony '{icon_data['name']}': {e}")
                
    # --- Metody otwierające aplikacje ---

    def open_image_viewer(self):
        if "image_viewer" not in self.app_windows or not self.app_windows["image_viewer"].winfo_exists():
            image_viewer_window = tk.Toplevel(self.root)
            self.app_windows["image_viewer"] = image_viewer_window
            ImageViewerApp(image_viewer_window)
            self.add_taskbar_button("image_viewer", "White War", image_viewer_window)
        else:
            self.app_windows["image_viewer"].lift()

    def open_yii_app(self):
        try:
            webbrowser.open("http://yii-application.test")
        except webbrowser.Error as e:
            messagebox.showerror("Error", f"Nie można otworzyć przeglądarki: {e}")

    def open_file_manager(self):
        if "file_manager" not in self.app_windows or not self.app_windows["file_manager"].winfo_exists():
            file_manager_window = tk.Toplevel(self.root)
            file_manager_window.title("File Manager (Simulated)")
            self.app_windows["file_manager"] = file_manager_window
            self.create_file_manager_widgets(file_manager_window)
            self.add_taskbar_button("file_manager", "File Manager", file_manager_window)
        else:
            self.app_windows["file_manager"].lift()

    def open_settings(self):
        if "settings" not in self.app_windows or not self.app_windows["settings"].winfo_exists():
            settings_window = tk.Toplevel(self.root)
            settings_window.title("Settings")
            self.app_windows["settings"] = settings_window
            self.create_settings_widgets(settings_window)
            self.add_taskbar_button("settings", "Settings", settings_window)
        else:
            self.app_windows["settings"].lift()

    def open_stock_analyzer(self):
        if "stock_analyzer" not in self.app_windows or not self.app_windows["stock_analyzer"].winfo_exists():
            stock_analyzer_window = tk.Toplevel(self.root)
            stock_analyzer_window.title("Stock Analyzer")
            self.app_windows["stock_analyzer"] = stock_analyzer_window
            self.create_stock_analyzer_widgets(stock_analyzer_window)
            self.add_taskbar_button("stock_analyzer", "Stock Analyzer", stock_analyzer_window)
        else:
            self.app_windows["stock_analyzer"].lift()

    def open_white_dwarf(self):
        if "white_dwarf" not in self.app_windows or not self.app_windows["white_dwarf"].winfo_exists():
            app_window = tk.Toplevel(self.root)
            app_window.title("White Dwarf Web Searcher")
            app_window.geometry("700x500")
            self.app_windows["white_dwarf"] = app_window
            self.create_white_dwarf_widgets(app_window)
            self.add_taskbar_button("white_dwarf", "Web Searcher", app_window)
        else:
            self.app_windows["white_dwarf"].lift()

    # --- Metody tworzące widgety dla aplikacji ---

    def create_file_manager_widgets(self, parent):
        file_frame = ttk.LabelFrame(parent, text="File List")
        file_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.file_listbox = tk.Listbox(file_frame, width=50)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        self.update_file_list()

        op_frame = ttk.LabelFrame(parent, text="Operations")
        op_frame.pack(padx=10, pady=5, fill=tk.X)
        self.file_name_entry = ttk.Entry(op_frame, width=20)
        self.file_name_entry.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(op_frame, text="Create File", command=self.create_new_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="Open", command=self.open_selected_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="Delete", command=self.delete_selected_file).pack(side=tk.LEFT, padx=5)
        
    def create_settings_widgets(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.create_network_settings(notebook)
        self.create_personalization_settings(notebook)

    def create_network_settings(self, notebook):
        net_frame = ttk.Frame(notebook)
        notebook.add(net_frame, text="Network")
        ttk.Label(net_frame, text="IP Address:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.ip_display = ttk.Label(net_frame, text="N/A")
        self.ip_display.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(net_frame, text="Hostname:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.hostname_display = ttk.Label(net_frame, text="N/A")
        self.hostname_display.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.update_ip_address()
        self.update_hostname()

    def create_personalization_settings(self, notebook):
        pers_frame = ttk.Frame(notebook)
        notebook.add(pers_frame, text="Personalization")
        ttk.Label(pers_frame, text="Desktop Background:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(pers_frame, text="Choose Color", command=self.choose_background_color).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

    def create_stock_analyzer_widgets(self, parent):
        tk.Label(parent, text="Stock Symbol:").pack(pady=5)
        self.stock_entry = tk.Entry(parent, width=20)
        self.stock_entry.pack(pady=5)
        self.stock_entry.insert(0, "AAPL")
        search_button = tk.Button(parent, text="Search & Plot", command=self.search_stock)
        search_button.pack(pady=10)
        self.result_box = scrolledtext.ScrolledText(parent, width=60, height=5)
        self.result_box.pack(pady=5, padx=5, fill="both", expand=True)

    def create_white_dwarf_widgets(self, parent):
        # Frame for input fields
        input_frame = tk.Frame(parent)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(input_frame, text="Adres URL:").pack(side=tk.LEFT)
        self.dwarf_url_entry = tk.Entry(input_frame)
        self.dwarf_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.dwarf_url_entry.insert(0, "https://en.wikipedia.org/wiki/Python_(programming_language)")

        # Frame for query
        query_frame = tk.Frame(parent)
        query_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(query_frame, text="Szukana fraza:").pack(side=tk.LEFT)
        self.dwarf_query_entry = tk.Entry(query_frame)
        self.dwarf_query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.dwarf_query_entry.insert(0, "type system")
        
        # Search button and sentiment label
        action_frame = tk.Frame(parent)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(action_frame, text="Szukaj", command=self._perform_web_search).pack(side=tk.LEFT)
        self.dwarf_sentiment_label = tk.Label(action_frame, text="Sentyment: -", font=("Arial", 12, "bold"))
        self.dwarf_sentiment_label.pack(side=tk.LEFT, padx=20)
        
        # Result box
        self.dwarf_result_box = scrolledtext.ScrolledText(parent, width=80, height=20)
        self.dwarf_result_box.pack(padx=10, pady=10, fill="both", expand=True)
        
    # --- Metody obsługujące logikę aplikacji ---

    def update_file_list(self):
        if self.file_listbox.winfo_exists():
            self.file_listbox.delete(0, tk.END)
            for file_name in self.filesystem.files.keys():
                self.file_listbox.insert(tk.END, file_name)

    def create_new_file(self):
        name = self.file_name_entry.get()
        if name:
            if self.filesystem.create_file(name): # POPRAWKA: self.filesystem
                self.update_file_list()
                messagebox.showinfo("Success", f"File '{name}' created")
            else:
                messagebox.showerror("Error", f"File '{name}' already exists")
        else:
            messagebox.showerror("Error", "File name cannot be empty")

    def open_selected_file(self):
        selected_indices = self.file_listbox.curselection()
        if selected_indices:
            file_name = self.file_listbox.get(selected_indices[0])
            content = self.filesystem.read_file(file_name) # POPRAWKA: self.filesystem
            self.show_file_content(file_name, content)

    def delete_selected_file(self):
        selected_indices = self.file_listbox.curselection()
        if selected_indices:
            file_name = self.file_listbox.get(selected_indices[0])
            if self.filesystem.delete_file(file_name): # POPRAWKA: self.filesystem
                self.update_file_list()
                messagebox.showinfo("Success", f"File '{file_name}' deleted")

    def show_file_content(self, file_name, content):
        if file_name not in self.app_windows or not self.app_windows[file_name].winfo_exists():
            file_window = tk.Toplevel(self.root)
            file_window.title(f"Content: {file_name}")
            text_area = scrolledtext.ScrolledText(file_window, width=50, height=20)
            text_area.insert(tk.END, content)
            text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            self.app_windows[file_name] = file_window
            self.add_taskbar_button(file_name, f"File: {file_name}", file_window)
        else:
            self.app_windows[file_name].lift()

    def update_ip_address(self):
        try:
            self.ip_display.config(text=socket.gethostbyname(socket.gethostname()))
        except Exception:
            self.ip_display.config(text="Not Available")

    def update_hostname(self):
        try:
            self.hostname_display.config(text=socket.gethostname())
        except Exception:
            self.hostname_display.config(text="Not Available")

    def choose_background_color(self):
        color = colorchooser.askcolor(title="Choose Background Color")[1]
        if color:
            self.desktop_bg_color = color
            self.desktop.config(bg=self.desktop_bg_color)
            for widget in self.desktop.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.config(bg=self.desktop_bg_color)
    
    def search_stock(self):
        symbol = self.stock_entry.get().upper()
        if not symbol:
            messagebox.showerror("Error", "Stock symbol cannot be empty.")
            return
            
        self.result_box.delete(1.0, tk.END)
        self.result_box.insert(tk.END, f"Searching for {symbol}...")
        self.root.update_idletasks() # Force GUI update
        
        try:
            response = requests.post("http://localhost:8888/stock", json={"symbol": symbol})
            data = response.json()
            
            self.result_box.delete(1.0, tk.END)
            if response.status_code == 200:
                self.result_box.insert(tk.END, f"Data saved: {data['path']}")
                self.show_stock_plot(data['path'])
            else:
                self.result_box.insert(tk.END, "Error: " + data.get("error", "Unknown error"))
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Error", "Could not connect to the local server. Is it running?")
            self.result_box.delete(1.0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.result_box.delete(1.0, tk.END)

    def _perform_web_search(self):
        url = self.dwarf_url_entry.get()
        query = self.dwarf_query_entry.get()
        if not url or not query:
            messagebox.showerror("Error", "URL and query cannot be empty.")
            return

        try:
            response = requests.post("http://localhost:8888/websearch", json={"url": url, "query": query})
            data = response.json()
            
            self.dwarf_result_box.delete(1.0, tk.END)
            if response.status_code == 200:
                self.dwarf_result_box.insert(tk.END, data["results"])
                self.dwarf_sentiment_label.config(text=f"Sentyment: {data['sentiment']}")
            else:
                self.dwarf_result_box.insert(tk.END, "Błąd: " + data.get("error", "Nieznany błąd"))
                self.dwarf_sentiment_label.config(text="Sentyment: -")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Błąd", "Nie można połączyć się z serwerem.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nieoczekiwany błąd: {e}")
            
    def show_stock_plot(self, file_path):
        try:
            df = pd.read_csv(file_path)
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
            df["Close"] = pd.to_numeric(df["Close"].str.replace(',', ''), errors='coerce')
            df = df.dropna(subset=['Date', 'Close'])
            df = df.sort_values(by="Date")

            plt.figure(figsize=(10, 5))
            plt.plot(df["Date"], df["Close"], marker='.', linestyle='-')
            plt.xlabel("Date")
            plt.ylabel("Closing Price (USD)")
            plt.title(f"Stock Price History for {os.path.basename(file_path).split('_')[0]}")
            plt.xticks(rotation=45)
            plt.grid(True)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            messagebox.showerror("Error", f"Could not display plot: {e}")

    # --- Zarządzanie oknami i serwerem ---

    def add_taskbar_button(self, app_key, app_name, window):
        button = ttk.Button(self.task_button_area, text=app_name, command=lambda win=window: self.handle_taskbar_button_click(win))
        button.pack(side=tk.LEFT, padx=2, pady=2)
        self.taskbar_buttons[app_key] = button

        def on_close():
            button.destroy()
            del self.taskbar_buttons[app_key]
            if app_key in self.app_windows:
                del self.app_windows[app_key]
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def handle_taskbar_button_click(self, window):
        if window.winfo_viewable():
            window.withdraw()
        else:
            window.deiconify()
            window.lift()

    def run_tornado(self):
        try:
            app = tornado.web.Application([
                (r"/stock", StockSearchHandler),
                (r"/websearch", WebSearchHandler)
            ])
            app.listen(8888)
            print("✅ Serwer Tornado działa na http://localhost:8888")
            tornado.ioloop.IOLoop.current().start()
        except OSError as e:
            if e.errno == 10048: # Port jest zajęty
                print("❌ BŁĄD: Port 8888 jest już zajęty. Uruchomienie serwera nie powiodło się.")
                messagebox.showerror("Błąd serwera", "Port 8888 jest zajęty. Aplikacje sieciowe nie będą działać.")
            else:
                print(f"❌ Błąd serwera Tornado: {e}")
        except Exception as e:
            print(f"❌ Nieznany błąd serwera Tornado: {e}")

    def start_tornado_server(self):
        if self.tornado_thread is None or not self.tornado_thread.is_alive():
            self.tornado_thread = threading.Thread(target=self.run_tornado, daemon=True)
            self.tornado_thread.start()
        else:
            print("Serwer Tornado już działa.")

    def stop_tornado_server(self):
        if self.tornado_thread and self.tornado_thread.is_alive():
            # Zatrzymaj pętlę IOLoop z wątku, w którym działa
            io_loop = tornado.ioloop.IOLoop.current(instance=False)
            if io_loop:
                io_loop.add_callback(io_loop.stop)
            print("Serwer Tornado zatrzymany.")
        else:
            print("Serwer Tornado nie był uruchomiony.")

# --- Główny punkt startowy aplikacji ---

if __name__ == "__main__":
    setup_db()  # Przygotuj bazę danych przy starcie
    
    root = tk.Tk()
    root.title("WW Space")
    root.geometry("1024x768")
    
    my_os = OS(root)

    # Poprawiony protokół zamykania
    def on_closing():
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            my_os.stop_tornado_server()
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()