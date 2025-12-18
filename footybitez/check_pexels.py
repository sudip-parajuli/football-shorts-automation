import os
import requests
from dotenv import load_dotenv

def check_pexels():
    load_dotenv()
    api_key = os.getenv("PEXELS_API_KEY")
    print(f"Loaded Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
    
    if not api_key:
        print("ERROR: PEXELS_API_KEY is missing.")
        return

    headers = {'Authorization': api_key}
    url = "https://api.pexels.com/videos/search?query=football&per_page=1"
    
    print(f"Testing URL: {url}")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS: Connection established.")
            data = response.json()
            if data.get('videos'):
                print(f"Found video: {data['videos'][0]['url']}")
            else:
                print("Response valid but no videos found.")
        else:
            print(f"FAILURE: {response.text}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    check_pexels()
