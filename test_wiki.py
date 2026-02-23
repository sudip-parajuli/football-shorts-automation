import wikipedia

query = "Chelsea's billion pound squad"
search_res = wikipedia.search(query, results=1)
print(f"Query: {query}")
print(f"Results: {search_res}")
if search_res:
    page = wikipedia.page(search_res[0], auto_suggest=False)
    print(f"Page Title: {page.title}")
    print(f"Page Summary: {page.summary[:200]}...")
