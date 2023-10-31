import re

def slugify(filename):
    # Remove all characters that are not allowed in filenames
    safe_filename = re.sub(r'[^\w\s-]', '', filename.lower()).strip()
    # Replace all spaces with hyphens
    safe_filename = re.sub(r'\s+', '-', safe_filename)
    return safe_filename

def snake_case(s):
  return '_'.join(
    re.sub('([A-Z][a-z]+)', r' \1',
    re.sub('([A-Z]+)', r' \1',
    s.replace('-', ' '))).split()).lower()
