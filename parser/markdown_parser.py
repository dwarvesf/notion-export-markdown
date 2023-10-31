# Most of the code was taken from the Notion2md repository
# https://github.com/echo724/notion2md/tree/main/notion2md

from pathlib import Path
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.parse import unquote
from . import utils


def paragraph(information: dict) -> str:
    return information['rich_text']


def heading_1(information: dict) -> str:
    return f"# {information['rich_text']}"


def heading_2(information: dict) -> str:
    return f"## {information['rich_text']}"


def heading_3(information: dict) -> str:
    return f"### {information['rich_text']}"


def callout(information: dict) -> str:
    return f"{information.get('icon')} {information['rich_text']}"


def quote(information: dict) -> str:
    return f"> {information['rich_text']}"

# toggle item will be changed as bulleted list item


def bulleted_list_item(information: dict) -> str:
    return f"* {information['rich_text']}"

# numbering is not supported


def numbered_list_item(information: dict) -> str:
    """
    input: item:dict = {"number":int, "text":str}
    """
    return f"1. {information['rich_text']}"


def to_do(information: dict) -> str:
    """
    input: item:dict = {"checked":bool, "test":str}
    """
    return f"- {'[x]' if information['checked'] else '[ ]'} {information['rich_text']}"


def code(information: dict) -> str:
    """
    input: item:dict = {"language":str,"text":str}
    """
    return f"```{information['language'].replace(' ', '_')}\n{information['rich_text']}\n```"


def embed(information: dict) -> str:
    """
    input: item:dict ={"url":str,"text":str}
    """
    embed_link = information["url"]

    block_md = f"""<p><div class="res_emb_block">
<iframe width="640" height="480" src="{embed_link}" frameborder="0" allowfullscreen></iframe>
</div></p>"""

    return block_md


def image(information: dict) -> str:
    """
    input: item:dict ={"url":str,"text":str,"caption":str}
    """
    image_name = information['url']

    if information['caption']:
        return f"![{information['caption']}]({image_name})"
    else:
        return f"![]({image_name})"


def file(information: dict) -> str:
    filename = information['url']
    clean_url = urljoin(filename, urlparse(filename).path)
    return f"[📎 {unquote(Path(clean_url).name)}]({filename})"


def bookmark(information: dict) -> str:
    """
    input: item:dict ={"url":str,"text":str,"caption":str}
    """
    if information['caption']:
        return f"![{information['caption']}]({information['url']})"
    else:
        return f"![]({information['url']})"


def equation(information: dict) -> str:
    return f"$$ {information['rich_text']} $$"


def divider(information: dict) -> str:
    return f"---"


def blank() -> str:
    return "\n"


def table_row(information: list) -> list:
    """
    input: item:list = [[richtext],....]
    """
    column_list = []
    for column in information['cells']:
        column_list.append(richtext_convertor(column))
    return column_list


def video(information: dict) -> str:
    youtube_link = information["url"]
    clean_url = \
        urljoin(youtube_link, urlparse(youtube_link).path)
    is_webm = clean_url.endswith(".webm")
    if is_webm:
        block_md = f"""<p><video playsinline autoplay muted loop controls src="{youtube_link}"></video></p>"""
    else:
        youtube_link = youtube_link.replace("http://", "https://")

        block_md = f"""<p><div class="res_emb_block">
<iframe width="640" height="480" src="{youtube_link}" frameborder="0" allowfullscreen></iframe>
</div></p>"""

    return block_md


block_type_map = {
    "paragraph": paragraph,
    "heading_1": heading_1,
    "heading_2": heading_2,
    "heading_3": heading_3,
    "callout": callout,
    "toggle": bulleted_list_item,
    "quote": quote,
    "bulleted_list_item": bulleted_list_item,
    "numbered_list_item": numbered_list_item,
    "to_do": to_do,
    # "child_page": child_page,
    "code": code,
    "embed": embed,
    "image": image,
    "bookmark": bookmark,
    "equation": equation,
    "divider": divider,
    "file": file,
    'table_row': table_row,
    "video": video
}


def blocks_convertor(blocks: object, page_id) -> str:
    results = []
    for block in blocks["results"]:
        block_md = block_convertor(block, 0, page_id)
        results.append(block_md)

    outcome_blocks = "".join([result for result in results])
    return outcome_blocks


def information_collector(payload: dict, page_id) -> dict:
    information = dict()
    if "rich_text" in payload:
        information['rich_text'] = richtext_convertor(payload['rich_text'])
    if "icon" in payload and "emoji" in payload["icon"]:
        information['icon'] = payload['icon']['emoji']
    if "checked" in payload:
        information['checked'] = payload['checked']
    if "expression" in payload:
        information['rich_text'] = payload['expression']
    if "url" in payload:
        information['url'] = payload['url']
    if "caption" in payload:
        information['caption'] = richtext_convertor(payload['caption'])
    if "external" in payload:
        information['url'] = payload['external']['url']
    if "language" in payload:
        information['language'] = payload['language']

    # internal url
    if "file" in payload:
        information['url'] = payload['file']['url']
        clean_url = \
            urljoin(information['url'], urlparse(information['url']).path)
        is_webm = clean_url.endswith(".webm")

    # table cells
    if "cells" in payload:
        information['cells'] = payload['cells']

    return information


def block_convertor(block: object, depth=0, page_id='') -> str:
    outcome_block: str = ""
    block_type = block.get("type")

    if block_type in block_type_map:
        outcome_block = block_type_map[block_type](
            information_collector(block[block_type], page_id)) + "\n\n"
    else:
        outcome_block = f"<!-- {block_type} {block['id']} -->\n\n"

    if block_type == "code":
        outcome_block = outcome_block.rstrip(
            '\n').replace('\n', '\n'+'\t'*depth)
        outcome_block += '\n\n'

    if all(k in block for k in ("has_children", "children")):
        if block_type == 'table':
            depth += 1
            child_blocks = block["children"]
            table_list = []
            for cell_block in child_blocks:
                cell_block_type = cell_block['type']
                table_list.append(block_type_map[cell_block_type](
                    information_collector(cell_block[cell_block_type], page_id))
                )
            # convert to markdown table
            for index, value in enumerate(table_list):
                if index == 0:
                    outcome_block = " | " + \
                        " | ".join(value) + " | " + "\n"
                    outcome_block += " | " + \
                        " | ".join(['----'] * len(value)) + \
                        " | " + "\n"
                    continue
                outcome_block += " | " + \
                    " | ".join(value) + " | " + "\n"
            outcome_block += "\n"
        else:
            depth += 1
            child_blocks = block["children"]
            for block in child_blocks:
                # This is needed, because notion thinks, that if
                # the page contains numbered list, header 1 will be the
                # child block for it, which is strange.
                if block['type'] == "heading_1":
                    depth = 0
                block_md = block_convertor(block, depth, page_id)
                outcome_block += block_md

    return outcome_block

# Link


def text_link(item: dict):
    """
    input: item:dict ={"content":str,"link":str}
    """
    return f"[{item['content']}]({item['link']['url']})"

# Annotations


def bold(content: str):
    return f"**{content}**"


def italic(content: str):
    return f"*{content}*"


def strikethrough(content: str):
    return f"~~{content}~~"


def underline(content: str):
    return f"<u>{content}</u>"


def a_code(content: str):
    return f"`{content}`"


def color(content: str, color):
    return f"<span style='color:{color}'>{content}</span>"


def a_equation(content: str):
    return f"$ {content} $"


annotation_map = {
    "bold": bold,
    "italic": italic,
    "strikethrough": strikethrough,
    "underline": underline,
    "code": a_code,
}

# Mentions


def _mention_link(content, url):
    if "https://github.com/" in url:
        repo = Path(url).name
        return f'<a href="{url}" target="_blank"> <i class="fa fa-lg fa-github"> </i> {repo} </a>'
    else:
        return f"[{content}]({url})"


def user(information: dict):
    return f"({information['content']})"


def page(information: dict):
    return _mention_link(information['content'], information['url'])


def date(information: dict):
    return f"({information['content']})"


def database(information: dict):
    return _mention_link(information['content'], information['url'])


def link_preview(information: dict):
    return _mention_link(information['content'], information['url'])


def mention_information(payload: dict):
    information = dict()
    if payload['href']:
        information['url'] = payload['href']
        if payload['plain_text'] != "Untitled":
            information['content'] = payload['plain_text']
        else:
            information['content'] = payload['href']
    else:
        information['content'] = payload['plain_text']

    return information


mention_map = {
    "user": user,
    "page": page,
    "database": database,
    "date": date,
    "link_preview": link_preview
}


def richtext_word_converter(richtext: dict, title_mode=False) -> str:
    outcome_word = ""
    plain_text = richtext["plain_text"]
    if richtext['type'] == "equation":
        outcome_word = a_equation(plain_text)
        if title_mode:
            return outcome_word
    elif richtext['type'] == "mention":
        mention_type = richtext['mention']['type']
        if mention_type in mention_map:
            outcome_word = mention_map[mention_type](
                mention_information(richtext))
    else:
        if title_mode:
            outcome_word = plain_text
            return outcome_word
        if "href" in richtext:
            if richtext["href"]:
                outcome_word = text_link(richtext["text"])
            else:
                outcome_word = plain_text
        else:
            outcome_word = plain_text
        annot = richtext["annotations"]
        for key, transfer in annotation_map.items():
            if richtext["annotations"][key]:
                outcome_word = transfer(outcome_word)
        if annot["color"] != "default":
            outcome_word = color(outcome_word, annot["color"])
    return outcome_word


def richtext_convertor(richtext_list: list, title_mode=False) -> str:
    """
    title_mode: bool flag is needed for headers parsing (in case they contain)
    any latex expressions.
    """
    outcome_sentence = ""
    for richtext in richtext_list:
        outcome_sentence += richtext_word_converter(richtext, title_mode)
    return outcome_sentence


def grouping(page_md: str) -> str:
    page_md_fixed = []
    prev_line_type = ''
    for line in page_md.splitlines():
        line_type = ''
        norm_line = line.lstrip('\t').lstrip()
        if norm_line.startswith('- [ ]') or norm_line.startswith('- [x]'):
            line_type = 'checkbox'
        elif norm_line.startswith('* '):
            line_type = 'bullet'
        elif norm_line.startswith('1. '):
            line_type = 'numbered'

        if prev_line_type != '':
            if line == '':
                continue

        if line_type != prev_line_type:
            page_md_fixed.append('')

        page_md_fixed.append(line)
        prev_line_type = line_type
    return "\n".join(page_md_fixed)


def parse_markdown(page_id: str, block: dict, frontmatter: dict):
    metadata = '---\n'
    for key, value in frontmatter.items():
        metadata += f"{utils.snake_case(key)}: {value}\n"
    metadata += f"---\n\n"

    page_md = blocks_convertor(block, page_id)
    page_md = grouping(page_md)
    page_md = page_md.replace("\n\n\n", "\n\n")
    return metadata + page_md
