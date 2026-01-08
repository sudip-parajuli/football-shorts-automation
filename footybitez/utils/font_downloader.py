import os
import requests

def download_font(url, filename):
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fonts")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        print(f"Font already exists: {path}")
        return path
    
    print(f"Downloading {filename}...")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"Downloaded {path}")
            return path
        else:
             print(f"Failed to download {filename}: Status {r.status_code}")
             return None
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return None

if __name__ == "__main__":
    # Montserrat Black
    download_font("https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Black.ttf", "Montserrat-Black.ttf")
    # Using Anton as a robust alternative for 'The Bold Font' (Very similar heavy style)
    download_font("https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf", "TheBoldFont.ttf")
