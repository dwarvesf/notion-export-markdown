import dateutil.parser as dt_parser
import logging
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.parse import unquote
from urllib.error import HTTPError
from pathlib import Path
from . import markdown_parser
from urllib import request
from itertools import groupby

def recursive_search(key, dictionary):
    if hasattr(dictionary,"items"):
        for k, v in dictionary.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in recursive_search(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in recursive_search(key, d):
                        yield result

def parse_headers(raw_notion: dict) -> dict:
    notion_pages = {}
    for page_id, page in raw_notion.items():
        notion_pages[page_id] = {}
        notion_pages[page_id]["files"] = []

        # Page type. Could be "page", "database" or "db_entry"
        notion_pages[page_id]["type"] = page["object"]
        if page["parent"]["type"] in ["database_id"]:
            notion_pages[page_id]["type"] = "db_entry"

        # Title
        if notion_pages[page_id]["type"] == "page":
            if len(page["properties"]["title"]["title"]) > 0:
                notion_pages[page_id]["title"] = \
                    page["properties"]["title"]["title"][0]["plain_text"]
            else:
                notion_pages[page_id]["title"] = None
        elif notion_pages[page_id]["type"] == "database":
            if len(page["title"]) > 0:
                notion_pages[page_id]["title"] = \
                    page["title"][0]["text"]["content"]
            else:
                notion_pages[page_id]["title"] = None
        elif notion_pages[page_id]["type"] == "db_entry":
            res = recursive_search("title", page["properties"])
            res = list(res)[0]
            if len(res) > 0:
                # notion_pages[page_id]["title"] = res[0]["plain_text"]
                notion_pages[page_id]["title"] = \
                    markdown_parser.richtext_convertor(res, title_mode=True)
            else:
                notion_pages[page_id]["title"] = None
                logging.warning(f"🤖Empty database entries could break the site building 😫.")


        # Time
        notion_pages[page_id]["last_edited_time"] = \
            page["last_edited_time"]
        if notion_pages[page_id]["type"] == "db_entry":
            if "Date" in page["properties"].keys():
                if page["properties"]["Date"]["date"] is not None:
                    notion_pages[page_id]["date"] = \
                        page["properties"]["Date"]["date"]["start"]
                    if page["properties"]["Date"]["date"]["end"] is not None:
                        notion_pages[page_id]["date_end"] = \
                            page["properties"]["Date"]["date"]["end"]

        # Parent
        if "workspace" in page["parent"].keys():
            parent_id = None
            notion_pages[page_id]["parent"] = parent_id
        elif notion_pages[page_id]["type"] in ["page", "database"]:
            parent_id = page["parent"]["page_id"]
            notion_pages[page_id]["parent"] = parent_id
        elif notion_pages[page_id]["type"] == "db_entry":
            parent_id = page["parent"]["database_id"]
            notion_pages[page_id]["parent"] = parent_id

        # Children
        if "children" not in notion_pages[page_id].keys():
            notion_pages[page_id]["children"] = []

        if parent_id is not None and parent_id in notion_pages:
            notion_pages[parent_id]["children"].append(page_id)

        # Cover
        if page["cover"] is not None:
            cover = list(recursive_search("url", page["cover"]))[0]
            notion_pages[page_id]["cover"] = cover
            notion_pages[page_id]["files"].append(cover)

        else:
            notion_pages[page_id]["cover"] = None

        # Icon
        if type(page["icon"]) is dict:
            if "emoji" in page["icon"].keys():
                notion_pages[page_id]["emoji"] = \
                    page["icon"]["emoji"]
                notion_pages[page_id]["icon"] = None
            elif "file" in page["icon"]:
                icon = page["icon"]["file"]["url"]
                notion_pages[page_id]["icon"] = icon
                notion_pages[page_id]["files"].append(icon)
                notion_pages[page_id]["emoji"] = None
        else:
            notion_pages[page_id]["icon"] = None
            notion_pages[page_id]["emoji"] = None

    return notion_pages

def find_lists_in_dbs(structured_notion: dict):
    """Determines the rule for considering database as list rather than gallery.

    Each database by default is treated as gallery, but if any child page does
    not have a cover, we will treat it as list.
    """
    for page_id, page in structured_notion["pages"].items():
        if page["type"] == 'database':
            for child_id in page["children"]:
                if structured_notion["pages"][child_id]["cover"] is None:
                    structured_notion["pages"][page_id]["db_list"] = True
                    break

def parse_family_line(page_id: str, family_line: list, structured_notion: dict):
    """Parses the whole parental line for page with 'page_id'"""
    if page_id in structured_notion['pages'] and structured_notion['pages'][page_id]["parent"] is not None:
        par_id = structured_notion["pages"][page_id]["parent"]
        family_line.insert(0, par_id)
        family_line = parse_family_line(par_id, family_line, structured_notion)

    return family_line

def parse_family_lines(structured_notion: dict):
    for page_id, page in structured_notion["pages"].items():
        page["family_line"] = parse_family_line(page_id, [], structured_notion)

def generate_urls(page_id:str, structured_notion: dict, config: dict):
    """Generates url for each page nested in page with 'page_id'"""
    if structured_notion["pages"][page_id]["title"]:
        if page_id == structured_notion["root_page_id"]:
            if config["build_locally"]:
                f_name = structured_notion["pages"][page_id]["title"].replace(" ",
                                                                            "_")
                f_name = f_name.replace("$", "_")
                f_name = f_name.replace("\\", "_")
            else:
                f_name = 'index'

            f_name += '.html'

            if config["build_locally"]:
                f_url = str(Path(config["output_dir"]).resolve() / f_name)
            else:
                f_url = config["site_url"]
            structured_notion["pages"][page_id]["url"] = f_url
            structured_notion["urls"].append(f_url)
        else:
            if config["build_locally"]:
                parent_id = structured_notion["pages"][page_id]["parent"]
                parent_url = structured_notion["pages"][parent_id]["url"]
                f_name = structured_notion["pages"][page_id]["title"].replace(" ",
                                                                            "_")
                f_name = f_name.replace("$", "_")
                f_name = f_name.replace("\\", "_")

                f_url = Path(parent_url).parent.resolve()
                f_url = f_url / f_name / f_name
                f_url = str(f_url.resolve()) + '.html'
                while f_url in structured_notion["urls"]:
                    f_name += "_"
                    f_url = Path(parent_url).parent
                    f_url = f_url / f_name / f_name
                    f_url = str(f_url.resolve()) + '.html'
                structured_notion["pages"][page_id]["url"] = f_url
                structured_notion["urls"].append(f_url)
            else:
                parent_id = structured_notion["pages"][page_id]["parent"]
                parent_url = structured_notion["pages"][parent_id]["url"]
                parent_url += '/'
                f_name = structured_notion["pages"][page_id]["title"].replace(" ",
                                                                            "_")
                f_name = f_name.replace("$", "_")
                f_name = f_name.replace("\\", "_")
                f_url = urljoin(parent_url, f_name)
                while f_url in structured_notion["urls"]:
                    f_name += "_"
                    f_url = urljoin(parent_url, f_name)
                structured_notion["pages"][page_id]["url"] = f_url
                structured_notion["urls"].append(f_url)

        for child_id in structured_notion["pages"][page_id]["children"]:
            generate_urls(child_id, structured_notion, config)

# ======================
# Properties handlers
# ======================

def p_rich_text(property:dict)->str:
    md_property = markdown_parser.richtext_convertor(property['rich_text'])
    return md_property

def p_number(property:dict)->str:
    md_property = ''
    logging.debug('🤖 Only number in the number block is supported')
    if property['number'] is not None:
        md_property = str(property['number'])
    return md_property

def p_select(property:dict)->str:
    md_property = ''
    if property['select'] is not None:
        md_property += str(property['select']['name'])
    return md_property

def p_multi_select(property:dict)->str:
    md_property = ''
    for tag in property['multi_select']:
        md_property += tag['name'] + ', '
    return md_property.rstrip(', ')

def p_date(property:dict)->str:
    md_property = ''
    if property['date'] is not None:
        dt = property['date']['start']
        md_property += dt_parser.isoparse(dt).strftime("%Y-%m-%d")
        if property['date']['end'] is not None:
            dt = property['date']['end']
            md_property += ' - ' + dt_parser.isoparse(dt).strftime("%Y-%m-%d")
    return md_property

def p_people(property:dict)->str:
    md_property = ''
    for tag in property['people']:
        if 'name' in tag:
            md_property += tag['name'] + ', '
    return md_property.rstrip(', ')

def p_files(property:dict)->str:
    md_property = ''
    for file in property['files']:
        md_property += f"[📎]({file['file']['url']})" + ", "
    return md_property.rstrip(', ')

def p_checkbox(property:dict)->str:
    return f"- {'[x]' if property['checkbox'] else '[ ]'}"

def p_url(property:dict)->str:
    md_property = ''
    if property['url'] is not None:
        md_property = f"[🕸]({property['url']})"
    return md_property

def p_email(property:dict)->str:
    md_property = ''
    if property['email'] is not None:
        md_property = property['email']
    return md_property

def p_phone_number(property:dict)->str:
    md_property = ''
    if property['phone_number'] is not None:
        md_property = property['phone_number']
    return md_property

# def p_formula(property:dict)->str:
#     md_property = ''
#     return md_property

# def p_relation(property:dict)->str:
#     md_property = ''
#     return md_property

# def p_rollup(property:dict)->str:
#     md_property = ''
#     return md_property

def p_created_time(property:dict)->str:
    md_property = ''
    if property['created_time'] is not None:
        dt = property['created_time']
        md_property += dt_parser.isoparse(dt).strftime("%Y-%m-%d")
    return md_property

# def p_created_by(property:dict)->str:
#     md_property = ''
#     return md_property

def p_last_edited_time(property:dict)->str:
    md_property = ''
    if property['last_edited_time'] is not None:
        dt = property['last_edited_time']
        md_property += dt_parser.isoparse(dt).strftime("%Y-%m-%d")
    return md_property

# def p_last_edited_by(property:dict)->str:
#     md_property = ''
#     return md_property


def parse_frontmatter(page: dict):
    properties_map = {
        "rich_text": p_rich_text,
        "number": p_number,
        "select": p_select,
        "multi_select": p_multi_select,
        "date": p_date,
        "people": p_people,
        "files": p_files,
        "checkbox": p_checkbox,
        "url": p_url,
        "email": p_email,
        "phone_number": p_phone_number,
        # "formula": p_formula,
        # "relation": p_relation,
        # "rollup": p_rollup,
        "created_time": p_created_time,
        # "created_by": p_created_by,
        "last_edited_time": p_last_edited_time,
        # "last_edited_by": p_last_edited_by
    }
    page["frontmatter"] = {}
    for property_title, property in page.get("properties", {}).items():
        if property["type"] == "title":
            continue
        if property["type"] in properties_map:
            page["frontmatter"][property_title] = properties_map[property['type']](property)
    return page
