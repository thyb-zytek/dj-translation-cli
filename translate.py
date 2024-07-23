#!/usr/bin/env python
import os
import re
import sys
from typing import Annotated

import typer
from rich import print

from utils import (
    check_path,
    create_translation_csv,
    extract_msgs_from_file,
    extract_translations_from_csv,
    print_interactive_commands,
    prompt_for_translation,
    replace_translation_in_content,
)

WEBAPP_LOCALES_FOLDER = "/home/alexisthibault/work/dev/webapp/citymeo/locale"
LOCAL_FILE = "LC_MESSAGES/django.po"

app = typer.Typer(rich_markup_mode="rich", add_completion=False)

extract_app = typer.Typer(rich_markup_mode="rich")
app.add_typer(extract_app, name="extract")

replace_app = typer.Typer(rich_markup_mode="rich")
app.add_typer(replace_app, name="replace")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        language = typer.prompt(
            "Which language do you want to translate",
            prompt_suffix=" ? (just language code)",
        )

        if not os.path.exists(os.path.join(WEBAPP_LOCALES_FOLDER, language)):
            print(
                f"[bold red]:warning: Language `{language}` does not exist :warning:[/bold red]"
            )
            sys.exit(1)

        with open(os.path.join(WEBAPP_LOCALES_FOLDER, language, LOCAL_FILE)) as f:
            content = f.read()

        msgs = extract_msgs_from_file(content)
        if len(msgs) == 0:
            print(
                f"[bold green]:white_check_mark: No translation found for language `{language}`[/bold green]"
            )
            sys.exit(0)

        print_interactive_commands(len(msgs))
        translations = prompt_for_translation(msgs)
        content, stat = replace_translation_in_content(translations, content)

        print(
            f"[green]:white_check_mark:[/green] [bold green]{stat} translation(s) done.[/bold green]"
        )
        with open(os.path.join(WEBAPP_LOCALES_FOLDER, language, LOCAL_FILE), "w") as f:
            f.write(content)


@extract_app.callback(invoke_without_command=True)
def generate_list_of_translations(
    languages: Annotated[
        str, typer.Option("--lang", "-l", help="language of i18n file")
    ] = "all",
    path: Annotated[
        str, typer.Option("--path", "-p", help="path of extracted translations file")
    ] = "translations.csv",
):
    """
    :outbox_tray: [bold blue]Extract[/bold blue] all missing translations of django given language
    """

    try:
        path = check_path(path)
    except ValueError as exc:
        raise typer.BadParameter(exc.args[0])

    translation_languages = (
        re.findall("[a-z]{2}", languages) if languages != "all" else []
    )

    msgids = []
    stats = {}
    for locale in os.listdir(WEBAPP_LOCALES_FOLDER):
        if languages == "all" or locale in languages:
            if languages == "all":
                translation_languages.append(locale)
            with open(os.path.join(WEBAPP_LOCALES_FOLDER, locale, LOCAL_FILE)) as f:
                msgs = extract_msgs_from_file(f.read())
                if locale not in stats:
                    stats[locale] = 0
                stats[locale] += len(msgs)
                msgids.extend(msgs)

    translation_languages = [lang for lang in translation_languages if stats[lang] > 0]

    create_translation_csv(path, translation_languages, msgids)

    print(
        "[green]:white_check_mark:[/green] Extracted translations :arrow_forward: "
        f"{", ".join([f"{locale}: {count}" for locale, count in stats.items()])}"
    )


@replace_app.callback(invoke_without_command=True)
def replace_list_of_translations(
    path: Annotated[
        str,
        typer.Option(
            "--path", "-p", help="path of translations file to put in django i18n file"
        ),
    ] = "translations.csv",
):
    """
    :pencil: [bold red]Replace[/bold red] all missing translations of django given language
    """
    try:
        path = check_path(path)
    except ValueError as exc:
        raise typer.BadParameter(exc.args[0])

    msgs = extract_translations_from_csv(path)

    stats = {}
    for language in msgs.keys():
        with open(os.path.join(WEBAPP_LOCALES_FOLDER, language, LOCAL_FILE)) as f:
            content, stats[language] = replace_translation_in_content(
                msgs[language], f.read()
            )

        with open(os.path.join(WEBAPP_LOCALES_FOLDER, language, LOCAL_FILE), "w") as f:
            f.write(content)

    print(
        "[green]:white_check_mark:[/green] Replaced translations :arrow_forward: "
        f"{", ".join([f"{locale}: {count}" for locale, count in stats.items()])}"
    )


if __name__ == "__main__":
    app()
