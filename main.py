import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext, messagebox, filedialog, colorchooser, Listbox, Button, Frame, Canvas
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
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from bs4 import BeautifulSoup
import mysql.connector
from textblob import TextBlob
import numpy as np
from scipy import linalg
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
import sys
import asyncio
import csv
import shutil
import re
import random
import nmap
# NOWY KOD: Import potrzebny do łączenia linków względnych w crawlerze
from urllib.parse import urljoin, urlparse
# KONIEC NOWEGO KODU

# Stałe wyrażeń regularnych z [kod 2]
IP_ADDRESS_RE = re.compile(r"^(?=.*[^\.]$)((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.?){4}$")
MASK_BINARY_RE = re.compile(r"^1*0*$")


# --- Konfiguracja i funkcje pomocnicze ---

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "search_db",
    "port": 3306
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
            sentiment VARCHAR(255),
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

def get_dominant_sentiment(documents: list) -> str:
    """Analizuje listę zdań i zwraca najczęściej występujący sentyment."""
    if not documents:
        return "😐 Neutralne"
    sentiments = [analyze_sentiment(doc) for doc in documents]
    sentiment_counts = Counter(sentiments)
    if not sentiment_counts:
        return "😐 Neutralne"
    return sentiment_counts.most_common(1)[0][0]

def PCA(data_matrix, n_components):
    """Wykonuje analizę głównych składowych (PCA)."""
    mean_vec = np.mean(data_matrix, axis=0)
    centered_data = data_matrix - mean_vec
    cov_mat = np.cov(centered_data, rowvar=False)
    eigenvalues, eigenvectors = linalg.eig(cov_mat)
    eig_pairs = [(np.abs(eigenvalues[i]), eigenvectors[:, i]) for i in range(len(eigenvalues))]
    eig_pairs.sort(key=lambda x: x[0], reverse=True)
    matrix_w = np.hstack([eig_pairs[i][1].reshape(-1, 1) for i in range(n_components)]).real
    return centered_data.dot(matrix_w)

def run_pca_demonstration(documents: list):
    """Demonstruje wektoryzację tekstu, PCA i wizualizację."""
    print("--- Uruchamianie demonstracji PCA ---")

    if len(documents) < 2:
        print("Błąd PCA: Potrzebne są co najmniej 2 zdania do analizy.")
        messagebox.showinfo("Błąd PCA", "Potrzebne są co najmniej 2 zdania do przeprowadzenia analizy.")
        return

    try:
        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(documents).toarray()
    except ValueError:
        messagebox.showinfo("Błąd PCA", "Nie można przetworzyć tekstu (może być zbyt krótki).")
        return

    if X.shape[1] < 2:
        print("Błąd PCA: Potrzebne są co najmniej 2 unikalne słowa.")
        messagebox.showinfo("Błąd PCA", "Tekst zawiera zbyt mało unikalnych słów do analizy.")
        return

    X_pca = PCA(data_matrix=X, n_components=2)

    sentiments = [analyze_sentiment(doc) for doc in documents]
    colors_map = {"😊 Pozytywne": "green", "😞 Negatywne": "red", "😐 Neutralne": "blue"}
    colors = [colors_map.get(s, "gray") for s in sentiments]

    plt.style.use('seaborn-v0_8-darkgrid')
    plt.figure(figsize=(11, 8))
    plt.scatter(X_pca[:, 0], X_pca[:, 1], c=colors, s=60, alpha=0.8, edgecolors='w')

    for i, doc in enumerate(documents):
        plt.annotate(f"Zdanie {i + 1}", (X_pca[i, 0], X_pca[i, 1]), textcoords="offset points", xytext=(0, 10), ha='center')

    for sentiment, color in colors_map.items():
        plt.scatter([], [], c=color, label=sentiment)

    plt.title("Wizualizacja sentymentu zdań po redukcji wymiarowości PCA")
    plt.xlabel("Pierwsza główna składowa (PC1)")
    plt.ylabel("Druga główna składowa (PC2)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def BezPow(data):
    RS = data['rs'].drop_duplicates()
    positions = data['positions'].drop_duplicates()
    dx = pd.DataFrame(
        data.drop_duplicates(),
        columns=['chip_name', 'rs', 'allele_f', 'allele_t', 'chromosome', 'positions', 'snp_name']
    )
    return dx

def openCSV(path):
    with open(path) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        data = []
        for row in readCSV:
            data.append(row)
    dy = pd.DataFrame(data, columns=['chip_name', 'rs', 'allele_f', 'allele_t', 'chromosome', 'positions', 'snp_name'])
    return dy

def CompareTotal(data1, data2):
    for b in data1:
        if b in data1['rs'] and not data1['chromosome'] and not data1['positions'] and not data1['snp_name']:
            data1.remove(b)
    for c in data2:
        if c in data2['rs'] and not data2['chromosome'] and not data2['positions'] and not data2['snp_name']:
            data2.remove(c)
    return data1 + data2

def SaveFile(data, path):
    data.to_csv(path)

def open_white_dwarf(self):
    """Otwiera aplikację White Dwarf Web Searcher."""
    if "white_dwarf" not in self.app_windows or not self.app_windows["white_dwarf"].winfo_exists():
        win = tk.Toplevel(self.root)
        win.title("White Dwarf Web Searcher")
        win.geometry("700x500")
        self.app_windows["white_dwarf"] = win
        self.create_white_dwarf_widgets(win)
        self.add_taskbar_button("white_dwarf", "🔎 Web Search", win)
    else:
        self.app_windows["white_dwarf"].lift()


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
            response.raise_for_status()

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
        conn = None
        cursor = None
        try:
            data = json.loads(self.request.body)
            url = data.get("url")
            query = data.get("query")

            if not url or not query:
                self.set_status(400)
                self.write({"error": "URL i fraza są wymagane."})
                return

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            found_texts = [p.get_text(strip=True) for p in paragraphs if query.lower() in p.get_text().lower()]

            results = "\n\n".join(found_texts)
            if not results:
                results = "Brak wyników zawierających podaną frazę."

            sentences = [sentence.strip() for sentence in results.split('.') if sentence.strip()]
            sentiment = get_dominant_sentiment(sentences)

            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO search_results (url, query, result, sentiment) VALUES (%s, %s, %s, %s)",
                    (url, query, results, sentiment)
                )
                conn.commit()
            except mysql.connector.Error as db_err:
                print(f"Błąd zapisu do bazy danych: {db_err}")

            self.write({"results": results, "sentiment": sentiment})

        except requests.exceptions.RequestException as e:
            self.set_status(500)
            self.write({"error": f"Błąd połączenia z adresem URL: {e}"})
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()


# --- Symulacja Systemu Operacyjnego (Procesy, Pliki, Scheduler) ---
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
            self.output.append(self.target(*self.args))
        except Exception as e:
            self.output.append(f"Error: {e}")
        finally:
            self.status = "stopped"

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
        return self.files.get(name, None)

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
        self.root.title("White War Explorer")
        self.root.geometry("1200x600")

        self.current_directory = os.getcwd()
        self.default_image_path = os.path.join(self.current_directory, "img", "sys", "ikigai.jpeg")

        self.create_default_image_if_needed()
        self.setup_gui()
        self.populate_tree(self.current_directory, "")

    def create_default_image_if_needed(self):
        if not os.path.exists(self.default_image_path):
            try:
                os.makedirs(os.path.dirname(self.default_image_path), exist_ok=True)
                img = Image.new('RGB', (800, 600), color='gray')
                img.save(self.default_image_path)
            except Exception as e:
                print(f"Nie udało się stworzyć domyślnego obrazka: {e}")

    def setup_gui(self):
        main_frame = Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        tree_frame = Frame(main_frame)
        tree_frame.pack(side="left", fill="y", padx=5, pady=5)

        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode=tk.BROWSE)
        self.tree.pack(side="left", fill="y", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        ysb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.pack(side='right', fill='y')

        self.display_frame = Frame(main_frame, bg="black")
        self.display_frame.pack(side="right", fill="both", expand=True)

        self.canvas = Canvas(self.display_frame, bg="black")
        self.text_area = scrolledtext.ScrolledText(self.display_frame, wrap=tk.WORD, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")

        self.show_default_image()

    def populate_tree(self, parent_path, parent_node):
        if not os.path.isdir(parent_path): return
        items = sorted(os.listdir(parent_path), key=lambda x: (not os.path.isdir(os.path.join(parent_path, x)), x.lower()))
        for item_name in items:
            item_path = os.path.join(parent_path, item_name)
            node = self.tree.insert(parent_node, 'end', text=item_name, open=False, values=[item_path])
            if os.path.isdir(item_path):
                self.populate_tree(item_path, node)

    def on_tree_select(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            item_path = self.tree.item(selected_item[0], "values")[0]
            if os.path.isfile(item_path): self.show_file_content(item_path)

    def is_image_file(self, path):
        return path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp"))

    def is_text_file(self, path):
        return path.lower().endswith((".txt", ".log", ".py", ".md", ".json", ".csv"))

    def show_file_content(self, file_path):
        if self.is_image_file(file_path):
            self.show_image(file_path)
        elif self.is_text_file(file_path):
            self.show_text_content(file_path)
        else:
            if hasattr(self.root, 'my_os'):
                self.root.my_os.open_with_default_app(file_path)

    def show_image(self, image_path):
        try:
            self.text_area.pack_forget()
            self.canvas.pack(fill="both", expand=True)
            img = Image.open(image_path)
            self.canvas.update_idletasks()
            canvas_width, canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
            if canvas_width < 2 or canvas_height < 2: canvas_width, canvas_height = 800, 600
            img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width / 2, canvas_height / 2, image=photo, anchor="center")
            self.canvas.image = photo
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            self.show_default_image()

    def show_text_content(self, file_path):
        try:
            self.canvas.pack_forget()
            self.text_area.pack(fill="both", expand=True)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                self.text_area.delete('1.0', tk.END)
                self.text_area.insert('1.0', file.read())
        except Exception as e:
            self.text_area.delete('1.0', tk.END)
            self.text_area.insert('1.0', f"Error reading file: {e}")

    def show_default_image(self):
        if os.path.exists(self.default_image_path):
            self.show_image(self.default_image_path)
        else:
            self.text_area.pack_forget()
            self.canvas.pack(fill="both", expand=True)
            self.canvas.delete("all")

# --- Główna klasa systemu operacyjnego ---
class OS:
    def __init__(self, root):
        self.root = root
        self.root.my_os = self
        self.processes = {}
        self.filesystem = FileSystem()
        self.scheduler = Scheduler()
        self.app_windows = {}
        self.taskbar_buttons = {}
        self.desktop_bg_color = "#3d405b"
        self.create_desktop()
        self.create_taskbar()
        self.create_icons()
        self.update_time()
        self.tornado_thread = None
        self.start_tornado_server()
        self.network_addr_integer = None
        self.broadcast_addr_integer = None

    def create_desktop(self):
        self.desktop = tk.Frame(self.root, bg=self.desktop_bg_color)
        self.desktop.pack(fill=tk.BOTH, expand=True)

    def create_taskbar(self):
        self.taskbar = tk.Frame(self.root, bg="gray", height=30)
        self.taskbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.taskbar.pack_propagate(False)

        try:
            icon_path = os.path.join(os.getcwd(), "img", "sys", "sheild.jpeg")
            image = Image.open(icon_path).resize((22, 22), Image.Resampling.LANCZOS)
            self.start_icon_photo = ImageTk.PhotoImage(image)
            self.start_menu_button = tk.Button(self.taskbar, image=self.start_icon_photo, relief=tk.RAISED, borderwidth=2, command=self.show_start_menu)
            self.start_menu_button.image = self.start_icon_photo
        except FileNotFoundError:
            print("Ostrzeżenie: Nie znaleziono ikony 'sheild.jpeg'. Używam domyślnego tekstu.")
            self.start_menu_button = tk.Button(self.taskbar, text="🛡️", relief=tk.RAISED, borderwidth=2, bg="lightgray", font=("Segoe UI Emoji", 10), command=self.show_start_menu)

        self.start_menu_button.pack(side=tk.LEFT, padx=5, pady=2)
        self.start_menu = tk.Menu(self.root, tearoff=0)
        
        self.task_button_area = tk.Frame(self.taskbar, bg="gray")
        self.task_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.time_label = tk.Label(self.taskbar, text="", bg="gray", fg="white")
        self.time_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def show_start_menu(self):
        self.root.update_idletasks()
        x = self.start_menu_button.winfo_rootx()
        y = self.start_menu_button.winfo_rooty()
        menu_height = self.start_menu.winfo_reqheight()
        popup_y = y - menu_height
        try:
            self.start_menu.tk_popup(x, popup_y)
        finally:
            self.start_menu.grab_release()

    def update_time(self):
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self.update_time)

    def create_icons(self):
        sys_img_dir = os.path.join(os.getcwd(), "img", "sys")
        os.makedirs(sys_img_dir, exist_ok=True)
        icons_data = [
            {"name": "File Explorer", "icon": "folder_icon.png", "action": self.open_file_manager},
            {"name": "Pandas Analyzer", "icon": "chart_icon.png", "action": self.open_pandas_analyzer},
            {"name": "PCA Analyzer", "icon": "chart_icon.png", "action": self.open_pca_analyzer},
            {"name": "White Dwarf Search", "icon": "browser.png", "action": lambda: open_white_dwarf(self)},
            # ### NOWY KOD ###
            {"name": "Engine++ Crawler", "icon": "browser.png", "action": self.open_enginepp_crawler},
            # ### KONIEC NOWEGO KODU ###
            {"name": "WhiteDwarf Shodan", "icon": "browser.png", "action": self.open_white_dwarf_shodan},
            {"name": "Network Monitor", "icon": "network_monitor.png", "action": self.launch_java_app},
            {"name": "Nmap Scanner", "icon": "network_scanner.png", "action": self.open_nmap_scanner},
            {"name": "WitchCraft (Web)", "icon": "musical-note.png", "action": self.open_yii_app},
            {"name": "Settings", "icon": "settings_icon.png", "action": self.open_settings},
        ]
        for i, icon_data in enumerate(icons_data):
            try:
                icon_path = os.path.join(sys_img_dir, icon_data["icon"])
                if not os.path.exists(icon_path): Image.new('RGBA', (64, 64), (70, 130, 180, 255)).save(icon_path)
                image = Image.open(icon_path).resize((48, 48), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                label = tk.Label(self.desktop, image=photo, text=icon_data["name"], compound=tk.TOP, bg=self.desktop_bg_color, cursor="hand2", fg="white")
                label.image = photo
                label.grid(row=i // 8, column=i % 8, padx=15, pady=15)
                label.bind("<Double-1>", lambda e, action=icon_data["action"]: action())
                self.start_menu.add_command(label=icon_data["name"], command=icon_data["action"])
            except Exception as e:
                print(f"Błąd podczas tworzenia ikony '{icon_data['name']}': {e}")
        
        self.start_menu.add_separator()
        self.start_menu.add_command(label="Zamknij", command=self.shutdown)

    def shutdown(self):
        if messagebox.askokcancel("Zamknij", "Czy na pewno chcesz zamknąć system?"):
            self.stop_tornado_server()
            self.root.destroy()

    def open_white_dwarf_shodan(self):
        try:
            webbrowser.open("https://www.shodan.io")
        except webbrowser.Error as e:
            messagebox.showerror("Błąd", f"Nie można otworzyć przeglądarki: {e}")

    def launch_java_app(self):
        jar_path = "NetworkMonitor.jar"
        java_command = ["java", "-jar", jar_path]
        if not os.path.exists(jar_path):
            messagebox.showerror("Błąd", f"Nie można znaleźć pliku aplikacji Java: {jar_path}\nUpewnij się, że plik istnieje i ścieżka jest poprawna.")
            return
        try:
            print(f"Uruchamianie aplikacji Java: {' '.join(java_command)}")
            subprocess.Popen(java_command)
        except FileNotFoundError:
            messagebox.showerror("Błąd", "Polecenie 'java' nie zostało znalezione.\nCzy Java jest zainstalowana i znajduje się w ścieżce systemowej (PATH)?")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się uruchomić aplikacji Java: {e}")

    def open_yii_app(self):
        try:
            webbrowser.open("http://yii-application.test")
        except webbrowser.Error as e:
            messagebox.showerror("Error", f"Nie można otworzyć przeglądarki: {e}")

    def open_file_manager(self):
        if "file_manager" not in self.app_windows or not self.app_windows["file_manager"].winfo_exists():
            win = tk.Toplevel(self.root)
            win.title("File Explorer")
            self.app_windows["file_manager"] = win
            self.create_file_manager_widgets(win)
            self.add_taskbar_button("file_manager", "📁 Explorer", win)
        else:
            self.app_windows["file_manager"].lift()
    
    # ### NOWY KOD: POCZĄTEK METOD DLA APLIKACJI ENGINE++ CRAWLER ###
    def open_enginepp_crawler(self):
        """Otwiera aplikację Engine++ Crawler."""
        if "enginepp_crawler" not in self.app_windows or not self.app_windows["enginepp_crawler"].winfo_exists():
            win = tk.Toplevel(self.root)
            win.title("Engine++ Crawler")
            win.geometry("700x550")
            self.app_windows["enginepp_crawler"] = win
            self.create_enginepp_crawler_widgets(win)
            self.add_taskbar_button("enginepp_crawler", "🕷️ Crawler", win)
        else:
            self.app_windows["enginepp_crawler"].lift()

    def create_enginepp_crawler_widgets(self, parent):
        """Tworzy widżety dla aplikacji Engine++ Crawler."""
        input_frame = ttk.Frame(parent, padding="10")
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text="Start URL:").pack(side=tk.LEFT, padx=(0, 5))
        self.crawler_url_entry = ttk.Entry(input_frame, width=40)
        self.crawler_url_entry.insert(0, "http://google.com")
        self.crawler_url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.crawler_run_button = ttk.Button(input_frame, text="Start Crawl", command=self._run_crawl_thread)
        self.crawler_run_button.pack(side=tk.LEFT, padx=(10, 0))

        results_frame = ttk.Frame(parent, padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True)

        self.crawler_status_label = ttk.Label(results_frame, text="Gotowy.", font=("Helvetica", 10))
        self.crawler_status_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.crawler_results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.crawler_results_text.pack(fill=tk.BOTH, expand=True)

    def _run_crawl_thread(self):
        """Uruchamia crawling w osobnym wątku."""
        url = self.crawler_url_entry.get()
        if not url or not url.startswith(('http://', 'https://')):
            messagebox.showerror("Błąd", "Proszę podać prawidłowy adres URL (z http:// lub https://).")
            return

        self.crawler_run_button.config(state=tk.DISABLED)
        self.crawler_results_text.config(state=tk.NORMAL)
        self.crawler_results_text.delete('1.0', tk.END)
        self.crawler_results_text.config(state=tk.DISABLED)
        self.crawler_status_label.config(text=f"Crawling {url}...")

        crawl_thread = threading.Thread(
            target=self._perform_crawl,
            args=(url,),
            daemon=True
        )
        crawl_thread.start()

    def _perform_crawl(self, url):
        """Logika crawlingu (wykonywana w wątku)."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            links = set()
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                # Przekształć linki względne na bezwzględne
                absolute_url = urljoin(url, href)
                # Sprawdź, czy URL jest poprawny (ma schemat i domenę)
                parsed_url = urlparse(absolute_url)
                if bool(parsed_url.scheme) and bool(parsed_url.netloc):
                    links.add(absolute_url)
            
            result_list = sorted(list(links))
            self.root.after(0, self._update_crawler_gui, result_list)

        except requests.RequestException as e:
            error_msg = f"Błąd połączenia: {e}"
            self.root.after(0, self._update_crawler_gui, [error_msg], is_error=True)
        except Exception as e:
            error_msg = f"Wystąpił nieoczekiwany błąd: {e}"
            self.root.after(0, self._update_crawler_gui, [error_msg], is_error=True)

    def _update_crawler_gui(self, links, is_error=False):
        """Aktualizuje interfejs użytkownika crawlera po zakończeniu zadania."""
        self.crawler_results_text.config(state=tk.NORMAL)
        self.crawler_results_text.delete('1.0', tk.END)

        if not is_error:
            self.crawler_status_label.config(text=f"Zakończono. Znaleziono {len(links)} unikalnych linków.")
            if links:
                self.crawler_results_text.insert('1.0', "\n".join(links))
            else:
                self.crawler_results_text.insert('1.0', "Nie znaleziono żadnych linków na tej stronie.")
        else:
            self.crawler_status_label.config(text="Crawl nie powiódł się.")
            self.crawler_results_text.insert('1.0', links[0])

        self.crawler_results_text.config(state=tk.DISABLED)
        self.crawler_run_button.config(state=tk.NORMAL)
    # ### KONIEC NOWEGO KODU ###

    def open_nmap_scanner(self):
        """Otwiera aplikację Nmap Banner Scanner."""
        if "nmap_scanner" not in self.app_windows or not self.app_windows["nmap_scanner"].winfo_exists():
            win = tk.Toplevel(self.root)
            win.title("Nmap Banner Scanner")
            win.geometry("800x600")
            self.app_windows["nmap_scanner"] = win
            self.create_nmap_scanner_widgets(win)
            self.add_taskbar_button("nmap_scanner", "📡 Nmap Scan", win)
        else:
            self.app_windows["nmap_scanner"].lift()

    def create_nmap_scanner_widgets(self, parent):
        """Tworzy widżety dla aplikacji Nmap."""
        input_frame = ttk.Frame(parent, padding="10")
        input_frame.pack(fill=tk.X)
        ttk.Label(input_frame, text="Host:").pack(side=tk.LEFT, padx=(0, 5))
        self.nmap_host_entry = ttk.Entry(input_frame, width=20)
        self.nmap_host_entry.insert(0, "127.0.0.1")
        self.nmap_host_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Label(input_frame, text="First Port:").pack(side=tk.LEFT, padx=5)
        self.nmap_start_port_entry = ttk.Entry(input_frame, width=8)
        self.nmap_start_port_entry.insert(0, "1")
        self.nmap_start_port_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(input_frame, text="Last Port:").pack(side=tk.LEFT, padx=5)
        self.nmap_end_port_entry = ttk.Entry(input_frame, width=8)
        self.nmap_end_port_entry.insert(0, "1024")
        self.nmap_end_port_entry.pack(side=tk.LEFT, padx=5)
        self.nmap_run_button = ttk.Button(input_frame, text="Run Scan", command=self._run_nmap_scan_thread)
        self.nmap_run_button.pack(side=tk.LEFT, padx=(10, 0))
        main_results_frame = ttk.Frame(parent, padding="5")
        main_results_frame.pack(fill=tk.BOTH, expand=True)
        self.nmap_output_text = scrolledtext.ScrolledText(main_results_frame, height=10, wrap=tk.WORD)
        self.nmap_output_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.nmap_fig = Figure(figsize=(5, 3), dpi=100)
        self.nmap_plot = self.nmap_fig.add_subplot(111)
        self.nmap_canvas = FigureCanvasTkAgg(self.nmap_fig, master=main_results_frame)
        self.nmap_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.nmap_canvas.draw()

    def _run_nmap_scan_thread(self):
        """Uruchamia skanowanie Nmap w osobnym wątku, aby nie blokować GUI."""
        host = self.nmap_host_entry.get()
        try:
            p_start = int(self.nmap_start_port_entry.get())
            p_end = int(self.nmap_end_port_entry.get())
        except ValueError:
            messagebox.showerror("Błąd", "Porty muszą być liczbami całkowitymi.")
            return
        if not host:
            messagebox.showerror("Błąd", "Nazwa hosta nie może być pusta.")
            return
        self.nmap_run_button.config(state=tk.DISABLED)
        self.nmap_output_text.delete('1.0', tk.END)
        self.nmap_output_text.insert('1.0', f"Skanowanie {host} na portach {p_start}-{p_end}...\nTo może potrwać dłuższą chwilę.")
        self.nmap_plot.clear()
        self.nmap_canvas.draw()
        scan_thread = threading.Thread(target=self._perform_nmap_scan, args=(host, p_start, p_end), daemon=True)
        scan_thread.start()

    def _perform_nmap_scan(self, host, p_start, p_end):
        """Logika skanowania Nmap (wykonywana w wątku)."""
        try:
            nm = nmap.PortScanner()
            port_range = f"{p_start}-{p_end}"
            nm.scan(hosts=host, ports=port_range, arguments="-sV --script banner --host-timeout 15m --max-retries 2")
            open_ports, banner_sizes = [], []
            result_string = ""
            if host not in nm.all_hosts():
                result_string = f"Host {host} nie odpowiada lub jest niedostępny."
                self.root.after(0, self._update_nmap_gui, result_string, [], [])
                return
            for proto in nm[host].all_protocols():
                for port in sorted(nm[host][proto].keys()):
                    state = nm[host][proto][port]["state"]
                    if state != "open":
                        continue
                    service = nm[host][proto][port].get("name", "?")
                    product = nm[host][proto][port].get("product", "")
                    version = nm[host][proto][port].get("version", "")
                    extrainfo = nm[host][proto][port].get("extrainfo", "")
                    scripts = nm[host][proto][port].get("script", {})
                    banner = scripts.get("banner", "").strip().replace('\n', ' ').replace('\r', '')
                    line1 = f"TCP {port:>5} | {service:<10} | {' '.join(filter(None, [product, version, extrainfo]))}\n"
                    result_string += line1
                    if banner:
                        line2 = f"           banner: {banner}\n"
                        result_string += line2
                    open_ports.append(port)
                    banner_sizes.append(len(banner.encode()))
            if not open_ports:
                result_string += "\nBrak otwartych portów lub bannerów w podanym zakresie."
            self.root.after(0, self._update_nmap_gui, result_string, open_ports, banner_sizes)
        except nmap.nmap.PortScannerError as e:
            error_msg = f"Błąd Nmap: {e}\n\nSprawdź, czy Nmap jest zainstalowany i dostępny w ścieżce systemowej."
            self.root.after(0, self._update_nmap_gui, error_msg, [], [])
        except Exception as e:
            error_msg = f"Wystąpił nieoczekiwany błąd: {e}"
            self.root.after(0, self._update_nmap_gui, error_msg, [], [])

    def _update_nmap_gui(self, result_text, open_ports, banner_sizes):
        """Aktualizuje interfejs użytkownika Nmap Scanner po zakończeniu skanowania."""
        self.nmap_output_text.delete('1.0', tk.END)
        self.nmap_output_text.insert('1.0', result_text)
        self.nmap_plot.clear()
        if open_ports:
            host = self.nmap_host_entry.get()
            self.nmap_plot.plot(open_ports, banner_sizes, marker="o")
            self.nmap_plot.set_title(f"Rozmiar bannerów dla {host}")
            self.nmap_plot.set_xlabel("Port")
            self.nmap_plot.set_ylabel("Długość bannera (B)")
            self.nmap_plot.grid(True)
            self.nmap_fig.tight_layout()
        self.nmap_canvas.draw()
        self.nmap_run_button.config(state=tk.NORMAL)

    def open_settings(self):
        if "settings" not in self.app_windows or not self.app_windows["settings"].winfo_exists():
            win = tk.Toplevel(self.root)
            win.title("Settings")
            self.app_windows["settings"] = win
            self.create_settings_widgets(win)
            self.add_taskbar_button("settings", "⚙️ Settings", win)
        else:
            self.app_windows["settings"].lift()

    def open_pandas_analyzer(self):
        flista = filedialog.askopenfilenames(
            title="Wybierz 4 pliki do analizy",
            filetypes=[("ASC files", "*.asc"), ("All files", "*.*")]
        )
        if not flista: return
        if len(flista) != 4:
            messagebox.showerror("Błąd", f"Oczekiwano 4 plików, a wybrano {len(flista)}. Proszę spróbować ponownie.")
            return
        try:
            print("Rozpoczynam analizę plików...")
            PATH_1, PATH_2, PATH_3, PATH_4, PATH_5, PATH_6, PATH_7 = "path1.csv", "path2.csv", "path3.csv", "path4.csv", "path5.csv", "path6.csv", "path7.csv"
            print(f"Przetwarzanie: {flista[0]}")
            BTNGeen = openCSV(flista[0])
            BTNGeenBezPow = BezPow(BTNGeen)
            SaveFile(BTNGeenBezPow, PATH_1)
            print(f"Przetwarzanie: {flista[1]}")
            BTNIllumina = openCSV(flista[1])
            BTNIlluminaBezPow = BezPow(BTNIllumina)
            SaveFile(BTNIlluminaBezPow, PATH_2)
            BTNGeenIluminaCT = CompareTotal(BTNGeenBezPow, BTNIlluminaBezPow)
            SaveFile(BTNGeenIluminaCT, PATH_3)
            print(f"Przetwarzanie: {flista[2]}")
            UMDGeen = openCSV(flista[2])
            UMDGeenBezPow = BezPow(UMDGeen)
            SaveFile(UMDGeenBezPow, PATH_4)
            print(f"Przetwarzanie: {flista[3]}")
            UMDIllumina = openCSV(flista[3])
            UMDIlluminaBezPow = BezPow(UMDIllumina)
            SaveFile(UMDIlluminaBezPow, PATH_5)
            UMDGeenIluminaCT = CompareTotal(UMDGeenBezPow, UMDIlluminaBezPow)
            SaveFile(UMDGeenIluminaCT, PATH_6)
            BTNUMDGeenIluminaCT = CompareTotal(BTNGeenIluminaCT, UMDGeenIluminaCT)
            SaveFile(BTNUMDGeenIluminaCT, PATH_7)
            print("Analiza zakończona pomyślnie.")
            messagebox.showinfo("Sukces", "Analiza została pomyślnie zakończona.")
        except Exception as e:
            print(f"Wystąpił błąd: {e}")
            messagebox.showerror("Błąd przetwarzania", f"Wystąpił nieoczekiwany błąd podczas analizy plików:\n\n{e}")

    def open_pca_analyzer(self):
        flista = filedialog.askopenfilenames(
            title="Wybierz pliki do analizy PCA",
            filetypes=[("ASC files", "*.asc"), ("All files", "*.*")]
        )
        if not flista: return
        n = len(flista)
        colA, colB = np.loadtxt(flista[0], usecols=(0, 1), unpack=True)
        m = len(colB)
        E, D = np.zeros((m, n)), np.zeros((m, n))
        for i in range(n):
            colA, colB = np.loadtxt(flista[i], usecols=(0, 1), unpack=True)
            if len(colB) != m:
                messagebox.showerror('Błąd', 'Pliki mają różne długości!')
                return
            for j in range(m):
                E[j][i] = colA[j]
                D[j][i] = colB[j]
        plt.plot(D)
        plt.title("Dane wejściowe")
        plt.show()
        Drepp = np.zeros((m, n, n))
        for j in range(n):
            print(f"Obliczanie PCA dla {j+1} komponentów...")
            Drepp[:, :, j] = PCA(D, j + 1)
        pplist = np.zeros(n)
        for i in range(n):
            pplist[i] = np.sum(abs(Drepp[:, :, i] - D))
        plt.plot(pplist)
        plt.title("Suma błędów absolutnych vs. liczba komponentów")
        plt.xlabel("Liczba komponentów")
        plt.ylabel("Suma błędów")
        plt.show()
        num_components_to_plot = min(3, n-1)
        if num_components_to_plot >= 0:
            plt.plot(D, Drepp[:, :, num_components_to_plot], 'o', [0, 1.2], [0, 1.2], '-')
            plt.title(f"Dane oryginalne vs. odtworzone z {num_components_to_plot + 1} komponentów")
            plt.xlabel("Oryginalne")
            plt.ylabel("Odtworzone")
            plt.show()

    def create_file_manager_widgets(self, parent):
        main_frame = Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        op_frame = ttk.LabelFrame(main_frame, text="Operations")
        op_frame.pack(padx=10, pady=5, fill=tk.X)
        self.file_manager_entry = ttk.Entry(op_frame, width=20)
        self.file_manager_entry.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(op_frame, text="Create File", command=self.create_real_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="Open", command=self.open_selected_item_from_manager).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="Delete", command=self.delete_selected_item_from_manager).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="Refresh", command=self.refresh_file_tree).pack(side=tk.LEFT, padx=5)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.file_manager_tree = ttk.Treeview(tree_frame, show="tree", selectmode=tk.BROWSE)
        self.file_manager_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.file_manager_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.file_manager_tree.config(yscrollcommand=scrollbar.set)
        self.refresh_file_tree()

    def populate_file_tree(self, parent_path, parent_node):
        """Rekurencyjnie wypełnia Treeview strukturą plików i katalogów."""
        if not os.path.isdir(parent_path): return
        try:
            items = sorted(os.listdir(parent_path), key=lambda x: not os.path.isdir(os.path.join(parent_path, x)))
            for item_name in items:
                item_path = os.path.join(parent_path, item_name)
                node = self.file_manager_tree.insert(parent_node, 'end', text=item_name, open=False, values=[item_path])
                if os.path.isdir(item_path):
                    self.file_manager_tree.insert(node, 'end', text='...')
        except PermissionError:
            self.file_manager_tree.insert(parent_node, 'end', text='[Dostęp zabroniony]', open=False)

    def refresh_file_tree(self):
        """Czyści i ponownie wypełnia drzewo plików."""
        if hasattr(self, 'file_manager_tree') and self.file_manager_tree.winfo_exists():
            for i in self.file_manager_tree.get_children():
                self.file_manager_tree.delete(i)
            self.populate_file_tree(os.getcwd(), "")

    def open_with_default_app(self, file_path):
        """Otwiera plik za pomocą domyślnej aplikacji systemowej."""
        try:
            if sys.platform == "win32": os.startfile(file_path)
            elif sys.platform == "darwin": subprocess.run(['open', file_path], check=True)
            else: subprocess.run(['xdg-open', file_path], check=True)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można otworzyć pliku: {e}")

    def open_selected_item_from_manager(self):
        """Otwiera zaznaczony element z File Explorera."""
        selected_item = self.file_manager_tree.selection()
        if selected_item:
            item_path = self.file_manager_tree.item(selected_item[0], "values")[0]
            self.open_with_default_app(item_path)

    def delete_selected_item_from_manager(self):
        """Usuwa zaznaczony element z File Explorera."""
        selected_item = self.file_manager_tree.selection()
        if not selected_item:
            messagebox.showwarning("Uwaga", "Nie wybrano żadnego elementu.")
            return
        item_path = self.file_manager_tree.item(selected_item[0], "values")[0]
        item_name = os.path.basename(item_path)
        if messagebox.askyesno("Potwierdź usunięcie", f"Czy na pewno chcesz usunąć '{item_name}'?"):
            try:
                if os.path.isfile(item_path): os.remove(item_path)
                elif os.path.isdir(item_path): shutil.rmtree(item_path)
                messagebox.showinfo("Sukces", f"'{item_name}' został usunięty.")
                self.refresh_file_tree()
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się usunąć elementu: {e}")

    def create_real_file(self):
        """Tworzy nowy plik w zaznaczonym katalogu."""
        file_name = self.file_manager_entry.get()
        if not file_name:
            messagebox.showerror("Błąd", "Nazwa pliku nie może być pusta.")
            return
        selected_item = self.file_manager_tree.selection()
        if selected_item:
            parent_path = self.file_manager_tree.item(selected_item[0], "values")[0]
            if os.path.isfile(parent_path): parent_path = os.path.dirname(parent_path)
        else:
            parent_path = os.getcwd()
        new_file_path = os.path.join(parent_path, file_name)
        try:
            if not os.path.exists(new_file_path):
                with open(new_file_path, 'w') as f: pass
                messagebox.showinfo("Sukces", f"Utworzono plik '{file_name}'.")
                self.refresh_file_tree()
            else:
                messagebox.showerror("Błąd", "Plik o tej nazwie już istnieje w tej lokalizacji.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można utworzyć pliku: {e}")

    def create_settings_widgets(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        net_frame = ttk.Frame(notebook)
        notebook.add(net_frame, text="Network")
        pers_frame = ttk.Frame(notebook)
        notebook.add(pers_frame, text="Personalization")
        ttk.Label(net_frame, text="IP Address:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.ip_display = ttk.Label(net_frame, text="N/A")
        self.ip_display.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(net_frame, text="Hostname:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.hostname_display = ttk.Label(net_frame, text="N/A")
        self.hostname_display.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.update_network_info()
        ttk.Label(pers_frame, text="Desktop Background:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Button(pers_frame, text="Choose Color", command=self.choose_background_color).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        subnet_frame = ttk.Frame(notebook)
        notebook.add(subnet_frame, text="Subnet Calculator")
        ttk.Label(subnet_frame, text="IP Address:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.subnet_ip_entry = ttk.Entry(subnet_frame, width=30)
        self.subnet_ip_entry.grid(row=0, column=1, padx=5, pady=10, sticky=tk.W)
        self.subnet_ip_entry.insert(0, "192.168.10.5")
        ttk.Label(subnet_frame, text="Subnet Mask:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.subnet_mask_entry = ttk.Entry(subnet_frame, width=30)
        self.subnet_mask_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.subnet_mask_entry.insert(0, "255.255.255.0")
        ttk.Button(subnet_frame, text="Calculate", command=self._calculate_subnet_gui).grid(row=2, column=0, columnspan=2, pady=10)
        self.subnet_results_text = scrolledtext.ScrolledText(subnet_frame, height=10, wrap=tk.WORD)
        self.subnet_results_text.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        random_frame = ttk.Frame(subnet_frame)
        random_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(random_frame, text="Generate Random IP", command=self._generate_random_ip_gui).pack(side=tk.LEFT, padx=5)
        self.random_ip_label = ttk.Label(random_frame, text="<-- Click to generate", font=('Helvetica', 10, 'italic'))
        self.random_ip_label.pack(side=tk.LEFT, padx=5)

    def _ip_address_valid(self, ip_addr):
        return IP_ADDRESS_RE.match(ip_addr) is not None

    def _mask_valid(self, mask):
        if not self._ip_address_valid(mask): return False
        mask_binary = self._convert_ip_addr_decimal_to_binary(mask)
        return MASK_BINARY_RE.match(mask_binary) is not None

    def _convert_ip_addr_decimal_to_binary(self, ip_addr):
        return ''.join(['{0:08b}'.format(int(octet)) for octet in ip_addr.split('.')])

    def _convert_ip_addr_int_to_human(self, ip_addr_int):
        ip_addr_bin = '{0:032b}'.format(ip_addr_int)
        octets = [str(int(ip_addr_bin[i*8:(i+1)*8], 2)) for i in range(4)]
        return '.'.join(octets)

    def _calculate_subnet_gui(self):
        ip_addr, mask = self.subnet_ip_entry.get(), self.subnet_mask_entry.get()
        self.subnet_results_text.delete('1.0', tk.END)
        self.network_addr_integer, self.broadcast_addr_integer = None, None
        if not self._ip_address_valid(ip_addr):
            self.subnet_results_text.insert(tk.END, "Błąd: Nieprawidłowy format adresu IP.")
            return
        if not self._mask_valid(mask):
            self.subnet_results_text.insert(tk.END, "Błąd: Nieprawidłowy format maski podsieci.")
            return
        ip_addr_binary = self._convert_ip_addr_decimal_to_binary(ip_addr)
        mask_binary = self._convert_ip_addr_decimal_to_binary(mask)
        mask_num_ones = mask_binary.count('1')
        self.network_addr_integer = int(ip_addr_binary, 2) & int(mask_binary, 2)
        network_addr_str = self._convert_ip_addr_int_to_human(self.network_addr_integer)
        wildcard_integer = ~int(mask_binary, 2) & 0xffffffff
        wildcard_str = self._convert_ip_addr_int_to_human(wildcard_integer)
        self.broadcast_addr_integer = self.network_addr_integer | wildcard_integer
        broadcast_addr_str = self._convert_ip_addr_int_to_human(self.broadcast_addr_integer)
        if mask_num_ones == 32: num_hosts = 1
        elif mask_num_ones == 31: num_hosts = 2
        else: num_hosts = 2**(32 - mask_num_ones) - 2
        results = (f"Adres IP:\t\t{ip_addr}\n"
                   f"Maska podsieci:\t{mask} (/{mask_num_ones})\n"
                   f"--------------------------------------------------\n"
                   f"Adres sieci:\t\t{network_addr_str}\n"
                   f"Adres rozgłoszeniowy:\t{broadcast_addr_str}\n"
                   f"Maska Wildcard:\t{wildcard_str}\n"
                   f"Liczba hostów:\t\t{num_hosts if num_hosts > 0 else 0}\n")
        self.subnet_results_text.insert(tk.END, results)

    def _generate_random_ip_gui(self):
        if self.network_addr_integer is None or self.broadcast_addr_integer is None:
            messagebox.showwarning("Brak danych", "Najpierw oblicz parametry podsieci.")
            return
        mask_num_ones = self._convert_ip_addr_decimal_to_binary(self.subnet_mask_entry.get()).count('1')
        if mask_num_ones < 31:
             start_range = self.network_addr_integer + 1
             end_range = self.broadcast_addr_integer - 1
             if start_range > end_range:
                 self.random_ip_label.config(text="Brak dostępnych hostów")
                 return
        else:
             start_range = self.network_addr_integer
             end_range = self.broadcast_addr_integer
        random_ip_int = random.randint(start_range, end_range)
        random_ip_str = self._convert_ip_addr_int_to_human(random_ip_int)
        self.random_ip_label.config(text=random_ip_str)

    def create_white_dwarf_widgets(self, parent):
        input_frame = Frame(parent)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(input_frame, text="Adres URL:").pack(side=tk.LEFT)
        self.dwarf_url_entry = tk.Entry(input_frame)
        self.dwarf_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.dwarf_url_entry.insert(0, "https://www.reuters.com/technology/")
        query_frame = Frame(parent)
        query_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(query_frame, text="Szukana fraza:").pack(side=tk.LEFT)
        self.dwarf_query_entry = tk.Entry(query_frame)
        self.dwarf_query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.dwarf_query_entry.insert(0, "AI")
        action_frame = Frame(parent)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        Button(action_frame, text="Szukaj", command=self._perform_web_search).pack(side=tk.LEFT)
        self.dwarf_sentiment_label = tk.Label(action_frame, text="Sentyment: -", font=("Arial", 12, "bold"))
        self.dwarf_sentiment_label.pack(side=tk.LEFT, padx=20)
        Button(action_frame, text="Analiza PCA", command=self._run_pca_on_results).pack(side=tk.LEFT, padx=10)
        self.dwarf_result_box = scrolledtext.ScrolledText(parent, width=80, height=20)
        self.dwarf_result_box.pack(padx=10, pady=10, fill="both", expand=True)

    def update_network_info(self):
        def _get_info():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except Exception: ip = "Brak połączenia"
            try: hostname = socket.gethostname()
            except Exception: hostname = "Nieznany"
            self.root.after(0, lambda: self.ip_display.config(text=ip))
            self.root.after(0, lambda: self.hostname_display.config(text=hostname))
        threading.Thread(target=_get_info, daemon=True).start()

    def choose_background_color(self):
        color_code = colorchooser.askcolor(title="Choose Background Color")[1]
        if color_code:
            self.desktop_bg_color = color_code
            self.desktop.config(bg=self.desktop_bg_color)
            for widget in self.desktop.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.config(bg=self.desktop_bg_color)
    
    def _perform_web_search(self):
        url, query = self.dwarf_url_entry.get(), self.dwarf_query_entry.get()
        if not url or not query:
            messagebox.showwarning("Brak danych", "Proszę podać adres URL i szukaną frazę.")
            return
        self.dwarf_result_box.delete(1.0, tk.END)
        self.dwarf_result_box.insert(tk.END, "Przetwarzanie... Proszę czekać.")
        self.dwarf_sentiment_label.config(text="Sentyment: Analizowanie...")
        self.root.update_idletasks()
        threading.Thread(target=self._perform_web_search_thread, args=(url, query), daemon=True).start()

    def _perform_web_search_thread(self, url, query):
        try:
            server_url = "http://localhost:8889/websearch"
            response = requests.post(server_url, json={"url": url, "query": query}, timeout=20)
            response.raise_for_status()
            data = response.json()
            self.dwarf_result_box.delete(1.0, tk.END)
            self.dwarf_result_box.insert(tk.END, data.get("results", "Brak wyników w odpowiedzi."))
            self.dwarf_sentiment_label.config(text=f"Sentyment: {data.get('sentiment', '-')}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Błąd Połączenia", f"Nie można połączyć się z serwerem: {e}")
            self.dwarf_result_box.delete(1.0, tk.END)
            self.dwarf_sentiment_label.config(text="Sentyment: -")
        except Exception as e:
            messagebox.showerror("Błąd Aplikacji", f"Wystąpił nieoczekiwany błąd: {e}")
            self.dwarf_result_box.delete(1.0, tk.END)
            self.dwarf_sentiment_label.config(text="Sentyment: -")

    def _run_pca_on_results(self):
        if "white_dwarf" not in self.app_windows or not self.app_windows["white_dwarf"].winfo_exists():
            messagebox.showinfo("Informacja", "Najpierw wykonaj wyszukiwanie, aby uzyskać tekst do analizy.")
            return
        results_text = self.dwarf_result_box.get("1.0", tk.END)
        if len(results_text.strip()) < 20:
            messagebox.showinfo("Informacja", "Brak wystarczającej ilości tekstu do przeprowadzenia analizy.")
            return
        sentences = [sentence.strip() for sentence in results_text.split('.') if sentence.strip()]
        if not sentences:
            messagebox.showinfo("Informacja", "Nie udało się podzielić tekstu na zdania do analizy.")
            return
        messagebox.showinfo("Uruchamianie analizy", "Analiza PCA zostanie uruchomiona w tle. Wykres pojawi się w nowym oknie.")
        threading.Thread(target=run_pca_demonstration, args=(sentences,), daemon=True).start()

    def add_taskbar_button(self, app_key, app_name, window):
        button = ttk.Button(self.task_button_area, text=app_name, command=lambda w=window: self.handle_taskbar_button_click(w))
        button.pack(side=tk.LEFT, padx=2, pady=2)
        self.taskbar_buttons[app_key] = button
        def on_close():
            button.destroy()
            if app_key in self.taskbar_buttons: del self.taskbar_buttons[app_key]
            if app_key in self.app_windows: del self.app_windows[app_key]
            window.destroy()
        window.protocol("WM_DELETE_WINDOW", on_close)

    def handle_taskbar_button_click(self, window):
        if window.winfo_viewable():
            window.iconify()
        else:
            window.deiconify()
            window.lift()

    def run_tornado(self):
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            app = tornado.web.Application([(r"/stock", StockSearchHandler), (r"/websearch", WebSearchHandler)])
            app.listen(8889, address="0.0.0.0")
            print("✅ Serwer Tornado działa na http://localhost:8889")
            tornado.ioloop.IOLoop.current().start()
        except OSError as e:
            if e.errno == 10048:
                print("❌ BŁĄD: Port 8889 jest już zajęty.")
                messagebox.showerror("Błąd serwera", "Port 8889 jest już zajęty.")
            else:
                print(f"❌ Błąd serwera Tornado (OSError): {e}")
        except Exception as e:
            print(f"❌ Nieznany błąd podczas uruchamiania serwera Tornado: {e}")

    def start_tornado_server(self):
        if self.tornado_thread is None or not self.tornado_thread.is_alive():
            self.tornado_thread = threading.Thread(target=self.run_tornado, name="TornadoServerThread", daemon=True)
            self.tornado_thread.start()
        else:
            print("Serwer Tornado już działa.")

    def stop_tornado_server(self):
        io_loop = tornado.ioloop.IOLoop.current(instance=False)
        if io_loop and io_loop.is_running():
            io_loop.add_callback(io_loop.stop)
            print("Wysłano żądanie zatrzymania serwera Tornado.")
        else:
            print("Serwer Tornado nie był uruchomiony lub został już zatrzymany.")


# --- Główny punkt startowy aplikacji ---

if __name__ == "__main__":
    setup_db()
    root = tk.Tk()
    root.title("SecureOS")
    root.geometry("1024x768")
    app = OS(root)
    root.mainloop()
    
    my_os = OS(root)
    
    root.protocol("WM_DELETE_WINDOW", my_os.shutdown)
    
    root.mainloop()