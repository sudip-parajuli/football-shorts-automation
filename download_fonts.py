import os
import requests

def download_file(url, save_path):
    print(f"Downloading {url} to {save_path}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
        return True
    except Exception as e:
        print(f"Failed to download: {e}")
        return False

def setup_fonts():
    font_dir = os.path.join(os.getcwd(), "footybitez", "data", "fonts")
    os.makedirs(font_dir, exist_ok=True)
    
    fonts = {
        "Montserrat-Black.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Black.ttf",
        # "TheBoldFont.ttf": "https://dl.dafont.com/dl/?f=the_bold_font" # Zip file, harder to automate directly without unzipping. 
        # Since TheBoldFont.ttf exists and size > 0, we assume it's fine for now, or we can try to find a raw ttf link if needed.
    }
    
    for filename, url in fonts.items():
        path = os.path.join(font_dir, filename)
        if not os.path.exists(path):
            download_file(url, path)
        else:
            print(f"{filename} already exists.")

if __name__ == "__main__":
    setup_fonts()
