import sys
import argparse
from pathlib import Path

from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup


def clean_text_preserving_gaps(soup):
    """Return normalized text with intentional blank gaps preserved."""
    for spacer in soup.select(".empty-line"):
        spacer.string = "\n"

    raw_text = soup.get_text(separator="\n", strip=False)
    lines = raw_text.splitlines()

    cleaned = []
    previous_blank = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if cleaned and not previous_blank:
                cleaned.append("")
            previous_blank = True
        else:
            cleaned.append(stripped)
            previous_blank = False

    return "\n".join(cleaned).strip()


def iter_documents_in_order(book):
    """Yield ITEM_DOCUMENT entries following the EPUB spine order."""
    seen_ids = set()

    # Respect the declared reading order (spine)
    for spine_item in book.spine:
        item_id = spine_item[0] if isinstance(spine_item, tuple) else spine_item
        item = book.get_item_with_id(item_id)
        if item and item.get_type() == ITEM_DOCUMENT:
            seen_ids.add(item_id)
            yield item

    # Fallback: include any remaining documents not referenced in the spine
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        if item.get_id() not in seen_ids:
            yield item

def epub_to_txt(epub_path, txt_path):
    book = epub.read_epub(epub_path)
    text_content = []

    for item in iter_documents_in_order(book):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = clean_text_preserving_gaps(soup)
        text_content.append(text)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(text_content))

    print(f"Converted '{epub_path}' → '{txt_path}' (full book).")


def convert_directory(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.is_dir():
        raise ValueError(f"Input directory '{input_dir}' does not exist or is not a directory.")

    output_dir.mkdir(parents=True, exist_ok=True)

    epub_files = sorted(
        [path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() == ".epub"]
    )

    if not epub_files:
        print(f"No EPUB files found in '{input_dir}'.")
        return

    for epub_file in epub_files:
        target_txt = output_dir / (epub_file.stem + ".txt")
        epub_to_txt(str(epub_file), str(target_txt))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Convert EPUB files to plain text (single file or batch directory mode)."
    )
    parser.add_argument("--input-file", help="Path to the input EPUB file.")
    parser.add_argument("--output-file", help="Path to the output TXT file.")
    parser.add_argument("--input-dir", help="Directory containing EPUB files to convert.")
    parser.add_argument("--output-dir", help="Directory where TXT results will be written.")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    file_mode = args.input_file or args.output_file
    dir_mode = args.input_dir or args.output_dir

    if file_mode and dir_mode:
        parser.error("Specify either file arguments or directory arguments, not both.")

    if args.input_file or args.output_file:
        if not (args.input_file and args.output_file):
            parser.error("Both --input-file and --output-file must be provided for single-file conversion.")
        epub_to_txt(args.input_file, args.output_file)
    elif args.input_dir or args.output_dir:
        if not (args.input_dir and args.output_dir):
            parser.error("Both --input-dir and --output-dir must be provided for batch conversion.")
        convert_directory(args.input_dir, args.output_dir)
    else:
        parser.error(
            "Please provide either --input-file/--output-file for single conversion "
            "or --input-dir/--output-dir for batch conversion."
        )


if __name__ == "__main__":
    main()
