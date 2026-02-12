from footybitez.media.media_sourcer import MediaSourcer

def test_media_logic():
    ms = MediaSourcer()
    
    print("\n--- Test 1: Player Query (Messi) ---")
    # This won't actually download if we don't have API keys set correctly in env, 
    # but we are looking for the PRINT DEBUG output from the logic branch.
    # The method prints "DEBUG: Searching DDG for..."
    try:
        ms.get_profile_image("Lionel Messi")
    except Exception as e:
        print(f"Execution error (expected if no net/api): {e}")
        
    print("\n--- Test 2: Club Query (Liverpool FC) ---")
    try:
        ms.get_profile_image("Liverpool FC")
    except Exception as e:
         print(f"Execution error (expected if no net/api): {e}")

if __name__ == "__main__":
    test_media_logic()
