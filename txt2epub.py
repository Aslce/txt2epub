#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXT 转 EPUB 小工具（自动识别编码、自动分章节、生成目录）

用法：
    python txt2epub.py 小说.txt
    python txt2epub.py 小说.txt -t 书名 -a 作者 -c 封面.jpg
    python txt2epub.py 某个文件夹            # 批量转换文件夹里所有 .txt

依赖：pip install ebooklib
"""
import argparse
import html
import os
import re
import sys
import uuid

try:
    from ebooklib import epub
except ImportError:
    sys.exit("缺少 ebooklib，请先运行：pip install ebooklib")

# 章节标题规则：匹配“第X章/节/回/卷/集/部/篇”，以及序章、楔子、番外、后记等
CHAPTER_RE = re.compile(
    r"^[ \t　]*("
    r"第[零〇一二两三四五六七八九十百千万0-9０-９]+[章节回卷集部篇]"
    r"|序[章言]?|楔子|引子|前言|尾声|后记|番外|终章"
    r"|Chapter\s*\d+"
    r")[^\n]{0,40}$",
    re.IGNORECASE | re.MULTILINE,
)

CSS = """
body { font-family: serif; line-height: 1.8; margin: 0 5%; }
h2 { text-align: center; margin: 1.5em 0 1em; font-size: 1.3em; }
p { text-indent: 2em; margin: 0.3em 0; }
"""


def read_text(path):
    """依次尝试常见编码，返回文本和识别出的编码"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "gb18030", "big5", "utf-16"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8(有乱码字符被替换)"


def split_chapters(text):
    """按章节标题切分，返回 [(标题, 正文), ...]"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(CHAPTER_RE.finditer(text))
    if not matches:
        # 没识别到章节：每 300 行切一段，避免单页过大
        lines = text.split("\n")
        return [(f"第{i // 300 + 1}部分", "\n".join(lines[i:i + 300]))
                for i in range(0, len(lines), 300)]

    chapters = []
    preface = text[:matches[0].start()].strip()
    if preface:
        chapters.append(("前言", preface))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(0).strip(" \t　")
        body = text[m.end():end]
        chapters.append((title, body))
    return chapters


def to_html(title, body):
    paras = [line.strip(" \t　") for line in body.split("\n")]
    paras = "".join(f"<p>{html.escape(p)}</p>\n" for p in paras if p)
    return f"<h2>{html.escape(title)}</h2>\n{paras}"


def convert(txt_path, title=None, author=None, cover=None, out_path=None):
    text, enc = read_text(txt_path)
    title = title or os.path.splitext(os.path.basename(txt_path))[0]
    out_path = out_path or os.path.splitext(txt_path)[0] + ".epub"

    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language("zh")
    if author:
        book.add_author(author)
    if cover:
        with open(cover, "rb") as f:
            book.set_cover("cover" + os.path.splitext(cover)[1], f.read())

    style = epub.EpubItem(uid="style", file_name="style.css",
                          media_type="text/css", content=CSS)
    book.add_item(style)

    items = []
    for i, (ch_title, body) in enumerate(split_chapters(text), 1):
        ch = epub.EpubHtml(title=ch_title, file_name=f"chap_{i:04d}.xhtml", lang="zh")
        ch.content = to_html(ch_title, body)
        ch.add_item(style)
        book.add_item(ch)
        items.append(ch)

    book.toc = items
    book.spine = ["nav"] + items
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(out_path, book)
    print(f"✓ {os.path.basename(txt_path)} → {os.path.basename(out_path)}"
          f"（编码 {enc}，{len(items)} 章）")


def main():
    ap = argparse.ArgumentParser(description="TXT 转 EPUB")
    ap.add_argument("input", help="TXT 文件，或包含多个 TXT 的文件夹")
    ap.add_argument("-t", "--title", help="书名（默认用文件名）")
    ap.add_argument("-a", "--author", help="作者")
    ap.add_argument("-c", "--cover", help="封面图片路径（jpg/png）")
    args = ap.parse_args()

    if os.path.isdir(args.input):
        files = sorted(f for f in os.listdir(args.input) if f.lower().endswith(".txt"))
        if not files:
            sys.exit("文件夹里没有 .txt 文件")
        for f in files:
            convert(os.path.join(args.input, f), author=args.author)
    else:
        convert(args.input, args.title, args.author, args.cover)


if __name__ == "__main__":
    main()
