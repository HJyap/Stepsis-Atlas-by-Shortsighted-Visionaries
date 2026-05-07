import fitz  # This is PyMuPDF

# Open the stubborn PDF
doc = fitz.open("/Users/hongjayyap/Stepsis-Atlas-by-Shortsighted-Visionaries/articles/Gai_2022.pdf" )

# Read the last page (where your garbled text seems to be from)
page = doc[-1] 
text = page.get_text()

print(text)