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
from bs4 import BeautifulSoup
import mysql.connector
from textblob import TextBlob
import numpy as np
from scipy import linalg
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter
import sys
import asyncio
#import gi
import csv

#gi.require_version("Gtk", "3.0")
#from gi.repository import Gtk


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

def show_message_dialog(parent, message_type, title, text):
    """Funkcja pomocnicza do wyświetlania okien z komunikatami."""
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=message_type,
        buttons=Gtk.ButtonsType.OK,
        text=title
    )
    dialog.format_secondary_text(text)
    dialog.run()
    dialog.destroy()

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
            self.open_with_default_app(file_path)

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

    def open_with_default_app(self, file_path):
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.run(['open', file_path], check=True)
            else:
                subprocess.run(['xdg-open', file_path], check=True)
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
        self.desktop_bg_color = "#3d405b"
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
        self.taskbar.pack_propagate(False)
        self.start_menu_button = tk.Menubutton(self.taskbar, text="🚀", relief=tk.RAISED, borderwidth=2, bg="lightgray", font=("Segoe UI Emoji", 10))
        self.start_menu_button.pack(side=tk.LEFT, padx=5, pady=2)
        self.start_menu = tk.Menu(self.start_menu_button, tearoff=0)
        self.start_menu_button["menu"] = self.start_menu
        self.task_button_area = tk.Frame(self.taskbar, bg="gray")
        self.task_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.time_label = tk.Label(self.taskbar, text="", bg="gray", fg="white")
        self.time_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def update_time(self):
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self.update_time)

    def create_icons(self):
        sys_img_dir = os.path.join(os.getcwd(), "img", "sys")
        os.makedirs(sys_img_dir, exist_ok=True)
        icons_data = [
            {"name": "File Manager (Sim)", "icon": "folder_icon.png", "action": self.open_file_manager},
            {"name": "Pandas Analyzer", "icon": "chart_icon.png", "action": self.open_pandas_analyzer},
            {"name": "PCA Analyzer", "icon": "chart_icon.png", "action": self.open_pca_analyzer},
            {"name": "White Dwarf Search", "icon": "browser.png", "action": lambda: open_white_dwarf(self)},
            {"name": "WhiteDwarf Shodan", "icon": "browser.png", "action": self.open_white_dwarf_shodan},
            ### NOWOŚĆ: Ikona do uruchamiania aplikacji Java ###
            {"name": "Network Monitor", "icon": "programming.png", "action": self.launch_java_app},
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

    def open_white_dwarf_shodan(self):
        """Otwiera stronę shodan.io w domyślnej przeglądarce."""
        try:
            webbrowser.open("https://www.shodan.io")
        except webbrowser.Error as e:
            messagebox.showerror("Błąd", f"Nie można otworzyć przeglądarki: {e}")
            
    ### NOWOŚĆ: Nowa funkcja do uruchamiania zewnętrznej aplikacji Java ###
    def launch_java_app(self):
        """Uruchamia zewnętrzną aplikację Java."""
        # UWAGA: Zmień 'path/to/your/app.jar' na rzeczywistą ścieżkę do Twojego pliku .jar
        jar_path = "NetworkMonitor.jar"
        java_command = ["java", "-jar", jar_path]
        
        if not os.path.exists(jar_path):
            messagebox.showerror("Błąd", f"Nie można znaleźć pliku aplikacji Java: {jar_path}\nUpewnij się, że plik istnieje i ścieżka jest poprawna.")
            return

        try:
            print(f"Uruchamianie aplikacji Java: {' '.join(java_command)}")
            # Używamy Popen, aby nie blokować interfejsu graficznego
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
            win.title("File Manager (Simulated)")
            self.app_windows["file_manager"] = win
            self.create_file_manager_widgets(win)
            self.add_taskbar_button("file_manager", "📁 File Sim", win)
        else:
            self.app_windows["file_manager"].lift()

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
        dialog = Gtk.FileChooserDialog(
            title="Open...",
            parent=None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)

        file_filter = Gtk.FileFilter()
        file_filter.set_name("All files")
        file_filter.add_pattern("*.asc")
        dialog.add_filter(file_filter)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            flista = dialog.get_filenames()

            if len(flista) != 4:
                show_message_dialog(
                    dialog, Gtk.MessageType.ERROR, "Błąd",
                    f"Oczekiwano 4 plików, a wybrano {len(flista)}. Proszę spróbować ponownie."
                )
                dialog.destroy()
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
                show_message_dialog(
                    dialog, Gtk.MessageType.INFO, "Sukces", "Analiza została pomyślnie zakończona."
                )
            except Exception as e:
                print(f"Wystąpił błąd: {e}")
                show_message_dialog(
                    dialog, Gtk.MessageType.ERROR, "Błąd przetwarzania",
                    f"Wystąpił nieoczekiwany błąd podczas analizy plików:\n\n{e}"
                )

        dialog.destroy()

    def open_pca_analyzer(self):
        dialog = Gtk.FileChooserDialog(
            title="Open...",
            parent=None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)

        file_filter = Gtk.FileFilter()
        file_filter.set_name("All files")
        file_filter.add_pattern("*.asc")
        dialog.add_filter(file_filter)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            flista = dialog.get_filenames()
            n = len(flista)
            if n == 0:
                dialog.destroy()
                return

            colA, colB = np.loadtxt(flista[0], usecols=(0, 1), unpack=True)
            m = len(colB)
            E = np.zeros((m, n))
            D = np.zeros((m, n))

            for i in range(n):
                colA, colB = np.loadtxt(flista[i], usecols=(0, 1), unpack=True)
                if len(colB) != m:
                    print('Error: rozne dlugosci plikow!')
                    sys.exit()
                for j in range(m):
                    E[j][i] = colA[j]
                    D[j][i] = colB[j]

            plt.plot(D)
            plt.show()

            Drepp = np.zeros((m, n, n))
            for j in range(n):
                print(j)
                Drepp[:, :, j] = PCA(D, j + 1)

            pplist = np.zeros(n)
            for i in range(n):
                pplist[i] = np.sum(abs(Drepp[:, :, i] - D))

            plt.plot(pplist)
            plt.show()
            plt.plot(D, Drepp[:, :, 3], 'o', [0, 1.2], [0, 1.2], '-')
            plt.show()

        dialog.destroy()

    def create_file_manager_widgets(self, parent):
        file_frame = ttk.LabelFrame(parent, text="File List")
        file_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.file_listbox = Listbox(file_frame, width=50)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        self.update_file_list()
        op_frame = ttk.LabelFrame(parent, text="Operations")
        op_frame.pack(padx=10, pady=5, fill=tk.X)
        self.file_name_entry = ttk.Entry(op_frame, width=20)
        self.file_name_entry.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(op_frame, text="Create", command=self.create_new_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="Open", command=self.open_selected_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="Delete", command=self.delete_selected_file).pack(side=tk.LEFT, padx=5)

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

    def create_stock_analyzer_widgets(self, parent):
        tk.Label(parent, text="Stock Symbol:").pack(pady=5)
        self.stock_entry = tk.Entry(parent, width=20)
        self.stock_entry.pack(pady=5)
        self.stock_entry.insert(0, "AAPL")
        Button(parent, text="Search & Plot", command=self.search_stock).pack(pady=10)
        self.result_box_stock = scrolledtext.ScrolledText(parent, width=60, height=5)
        self.result_box_stock.pack(pady=5, padx=5, fill="both", expand=True)

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

    def update_file_list(self):
        if hasattr(self, 'file_listbox') and self.file_listbox.winfo_exists():
            self.file_listbox.delete(0, tk.END)
            for file_name in self.filesystem.files.keys():
                self.file_listbox.insert(tk.END, file_name)

    def create_new_file(self):
        name = self.file_name_entry.get()
        if name:
            if self.filesystem.create_file(name):
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
            file = self.filesystem.read_file(file_name)
            if file:
                self._show_simulated_file_content(file_name, file.content)

    def delete_selected_file(self):
        selected_indices = self.file_listbox.curselection()
        if selected_indices:
            file_name = self.file_listbox.get(selected_indices[0])
            if self.filesystem.delete_file(file_name):
                self.update_file_list()
                messagebox.showinfo("Success", f"File '{file_name}' deleted")

    def _show_simulated_file_content(self, file_name, content):
        win_key = f"file_sim_{file_name}"
        if win_key not in self.app_windows or not self.app_windows[win_key].winfo_exists():
            win = tk.Toplevel(self.root)
            win.title(f"Content: {file_name}")
            text_area = scrolledtext.ScrolledText(win, width=50, height=20)
            text_area.insert(tk.END, content if content is not None else "")
            text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            self.app_windows[win_key] = win
            self.add_taskbar_button(win_key, f"📄 {file_name}", win)
        else:
            self.app_windows[win_key].lift()

    def update_network_info(self):
        def _get_info():
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                ip = "Not Available"
            try:
                hostname = socket.gethostname()
            except Exception:
                hostname = "Not Available"
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

    def search_stock(self):
        symbol = self.stock_entry.get().upper()
        if not symbol:
            messagebox.showerror("Error", "Stock symbol cannot be empty.")
            return
        self.result_box_stock.delete(1.0, tk.END)
        self.result_box_stock.insert(tk.END, f"Searching for {symbol}...")
        self.root.update_idletasks()
        threading.Thread(target=self._search_stock_thread, args=(symbol,), daemon=True).start()

    def _search_stock_thread(self, symbol):
        try:
            response = requests.post("http://localhost:8889/stock", json={"symbol": symbol}, timeout=15)
            data = response.json()
            self.result_box_stock.delete(1.0, tk.END)
            if response.status_code == 200:
                path = data.get('path')
                self.result_box_stock.insert(tk.END, f"Data saved: {path}")
                self.show_stock_plot(path)
            else:
                self.result_box_stock.insert(tk.END, "Error: " + data.get("error", "Unknown error"))
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Could not connect to the local server.\n{e}")
            self.result_box_stock.delete(1.0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.result_box_stock.delete(1.0, tk.END)

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

    def show_stock_plot(self, file_path):
        try:
            df = pd.read_csv(file_path)
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
            df["Close"] = pd.to_numeric(df["Close"].astype(str).str.replace(',', ''), errors='coerce')
            df.dropna(subset=['Date', 'Close'], inplace=True)
            df.sort_values(by="Date", inplace=True)
            plt.style.use('seaborn-v0_8-darkgrid')
            plt.figure(figsize=(10, 5))
            plt.plot(df["Date"], df["Close"], marker='.', linestyle='-', color='#4ecca3')
            plt.xlabel("Date")
            plt.ylabel("Closing Price (USD)")
            plt.title(f"Stock Price History for {os.path.basename(file_path).split('_')[0]}")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            messagebox.showerror("Error", f"Could not display plot: {e}")

    def add_taskbar_button(self, app_key, app_name, window):
        button = ttk.Button(self.task_button_area, text=app_name, command=lambda w=window: self.handle_taskbar_button_click(w))
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
            window.iconify()
        else:
            window.deiconify()
            window.lift()

    def run_tornado(self):
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            app = tornado.web.Application([(r"/stock", StockSearchHandler), (r"/websearch", WebSearchHandler)])
            app.listen(8889)
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
    root.title("WW Space")
    root.geometry("1024x768")

    my_os = OS(root)

    def on_closing():
        if messagebox.askokcancel("Quit", "Czy na pewno chcesz zamknąć system?"):
            my_os.stop_tornado_server()
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()