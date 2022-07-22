import regex as re
from pywikibot import Page
from pywikibot.pagegenerators import AllpagesPageGenerator
from tqdm import tqdm

pattern = re.compile(r".*?:(.*)")


def create_redirect():
    """Create redirect [[stem]] for given [[prefix:stem]]."""
    for target in tqdm(AllpagesPageGenerator()):
        if match := pattern.fullmatch(target.title()):
            Page(target.site, match.group(1)).set_redirect_target(target, force=True)


if __name__ == "__main__":
    create_redirect()
