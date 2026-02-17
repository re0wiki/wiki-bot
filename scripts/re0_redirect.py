import regex as re
from pywikibot.pagegenerators import AllpagesPageGenerator
from tqdm import tqdm

from pywikibot import Page

pattern = re.compile(r".+?:(.+)")


def create_redirect():
    """Create redirect [[stem]] for given [[prefix:stem]]."""
    for target in tqdm(AllpagesPageGenerator(includeredirects=False)):
        if match := pattern.fullmatch(target.title()):
            if not (page := Page(target.site, match.group(1))).isRedirectPage():
                page.set_redirect_target(
                    target, force=True, summary=f"{page.title()} -> {target.title()}"
                )


if __name__ == "__main__":
    create_redirect()
