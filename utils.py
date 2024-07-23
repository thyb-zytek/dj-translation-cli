import csv
import os
import re
import sys

import typer
from prompt_toolkit import PromptSession
from rich import print
from rich.panel import Panel

FUZZY_REGEX = re.compile(r"#, fuzzy\n#\| msgid \".*\"\nmsgid \"(.*)\"\nmsgstr \"(.*)\"")
TRANSLATION_REGEX = re.compile(r"msgid \"(.*)\"\nmsgstr \"\"\n\n")
LONG_TRANSLATION_REGEX = re.compile(r"msgid \"\"((\n\"(.*?)\")+)\nmsgstr \"\"\n\n")


def extract_msgs_from_file(content: str) -> list[str]:
    msgs = TRANSLATION_REGEX.findall(content)
    for found in LONG_TRANSLATION_REGEX.finditer(content):
        msg_id = found.group(1).replace('"', "").replace("\n", "")
        msgs.append(msg_id)
    msgs.extend([found.group(1) for found in FUZZY_REGEX.finditer(content)])
    return msgs


def create_translation_csv(path: str, languages: list[str], msgids: list[str]):
    with open(path, "w") as csvfile:
        fieldnames = ["msgid", *languages]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows([{"msgid": msgid} for msgid in set(msgids)])


def extract_translations_from_csv(file_path: str) -> dict[str, dict[str, str]]:
    msgs = {}
    with open(file_path) as csvfile:
        reader = csv.DictReader(csvfile)
        languages = reader.fieldnames[1:]
        for row in reader:
            for language in languages:
                if language not in msgs:
                    msgs[language] = {}

                msgs[language][row["msgid"]] = row[language]

    return msgs


def replace_default_translation_in_file(
    content: str, msgs: dict[str, str]
) -> tuple[str, int]:
    nb_replaced = 0
    for found in TRANSLATION_REGEX.finditer(content):
        original_msg = found.group()
        msg_id = TRANSLATION_REGEX.search(original_msg).group(1)
        if msg_id not in msgs or not msgs[msg_id]:
            continue
        translated_msg = original_msg.replace('msgstr ""', f'msgstr "{msgs[msg_id]}"')
        content = content.replace(original_msg, translated_msg)
        nb_replaced += 1
    return content, nb_replaced


def replace_fuzzy_translation_in_file(
    content: str, msgs: dict[str, str]
) -> tuple[str, int]:
    nb_replaced = 0
    for found in FUZZY_REGEX.finditer(content):
        original_msg = found.group()
        msg_id = found.group(1)
        if msg_id not in msgs or not msgs[msg_id]:
            continue
        translated_msg = f'msgid "{msg_id}"\nmsgstr "{msgs[msg_id]}"\n\n'
        content = content.replace(original_msg, translated_msg)
        nb_replaced += 1
    return content, nb_replaced


def replace_long_translation_in_file(
    content: str, msgs: dict[str, str]
) -> tuple[str, int]:
    nb_replaced = 0
    for found in LONG_TRANSLATION_REGEX.finditer(content):
        original_msg = found.group(0)
        not_formatted_msg = found.group(1)
        msg_id = not_formatted_msg.replace('"', "").replace("\n", "")
        if msg_id not in msgs or not msgs[msg_id]:
            continue
        translated_msg = f'msgid ""{not_formatted_msg}\nmsgstr ""\n"{_wrap_string(msgs[msg_id])}"\n\n'
        content = content.replace(original_msg, translated_msg)
        nb_replaced += 1
    return content, nb_replaced


def replace_translation_in_content(
    msgs: dict[str, str], content: str
) -> tuple[str, int]:
    replaced = 0
    content, nb_replaced = replace_default_translation_in_file(content, msgs)
    replaced += nb_replaced
    content, nb_replaced = replace_fuzzy_translation_in_file(content, msgs)
    replaced += nb_replaced
    content, nb_replaced = replace_long_translation_in_file(content, msgs)
    replaced += nb_replaced

    # Clean content
    content.replace("\n\n\n\n", "\n\n")
    return content, replaced


def _wrap_string(string):
    lines = []
    current_line = ""
    for word in string.split():
        if len(current_line) + len(word) <= 80:
            current_line += " " + word
        else:
            lines.append(f'{current_line.strip()} "')
            current_line = '"' + word
    if current_line:
        lines.append(current_line.strip())
    return "\n".join(lines)


def check_path(path: str) -> str:
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        raise ValueError(f"Path `{dirname}` does not exist")

    if filename and not filename.endswith(".csv"):
        raise ValueError(f"Filename `{filename}` does not end with .csv")

    if dirname and filename:
        return path
    elif dirname and not filename:
        return os.path.join(dirname, "translations.csv")
    elif not dirname and filename:
        return os.path.join(os.getcwd(), filename)
    else:
        return os.path.join(os.getcwd(), "translations.csv")


def print_interactive_commands(nb_msg: int) -> None:
    print(
        Panel(
            (
                "List the translation messages and enter the translation you want. "
                "You can use the following commands to navigate.\n\n"
                "\t⬅️  [bold]:u[/bold] return to the previous translation message.\n"
                "\t➡️  [bold]:n[/bold] go to the next translation message.\n"
                "\t⏪ [bold]:b[/bold] return to the beginning.\n"
                "\t💾 [bold]:x[/bold] save and quit\n"
                "\t🛑 [bold]:q[/bold] quit without saving.\n"
            ),
            title=f"[green]:white_check_mark:[/green] [bold green]{nb_msg}[/bold green] translation found",
        )
    )


def prompt_for_translation(msgs: list[str]) -> dict[str, str]:
    translations = {}
    i = 0
    session = PromptSession()
    while i < len(msgs):
        print(f":arrow_forward: [bold]{msgs[i]}[/bold]")
        translation = session.prompt(
            "",
            default=translations.get(msgs[i], ""),
        )
        match translation:
            case "":
                typer.confirm(
                    "Are you sure you want to set a blank translation",
                    prompt_suffix="?",
                )
            case ":u":
                i -= 1
            case ":n":
                i += 1
            case ":b":
                i = 0
            case ":x":
                break
            case ":q":
                typer.confirm(
                    "Are you sure you want to quit without saving",
                    prompt_suffix="?",
                )
                sys.exit(0)
            case _:
                translations[msgs[i]] = translation
                i += 1

    return translations
