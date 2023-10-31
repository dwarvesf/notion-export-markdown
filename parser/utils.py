import re

def slugify(filename):
    # Remove all characters that are not allowed in filenames
    safe_filename = re.sub(r'[^\w\s-]', '', filename.lower()).strip()
    # Replace all spaces with hyphens
    safe_filename = re.sub(r'\s+', '-', safe_filename)
    return safe_filename
