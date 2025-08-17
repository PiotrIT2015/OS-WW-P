# Krok 1: Użyj oficjalnego, lekkiego obrazu Pythona jako obrazu bazowego.
FROM python:3.11-slim-buster

# Krok 2: Ustaw katalog roboczy w kontenerze.
WORKDIR /app

# Krok 3: Skopiuj plik z zależnościami i zainstaluj biblioteki.
# Wykorzystujemy mechanizm cache'owania warstw Dockera.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Krok 4: Skopiuj resztę kodu aplikacji do kontenera.
COPY . .

# Krok 5: Ustaw domyślną komendę, która uruchomi aplikację.
# Używamy Gunicorn do serwowania aplikacji na porcie 8000 wewnątrz kontenera.
# Apache będzie przekierowywać ruch na ten port.
CMD ["python", "main.py"]