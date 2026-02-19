import regex as re
from pywikibot.pagegenerators import GeneratorFactory

import pywikibot as pwb

REGEX = re.compile(r".+?:(.+)")


class RedirectBot(pwb.bot.SingleSiteBot, pwb.bot.ExistingPageBot):
    """Create redirect [[stem]] for given [[prefix:stem]]."""

    def treat_page(self) -> None:
        if match := REGEX.fullmatch(self.current_page.title()):
            if not (page := pwb.Page(self.site, match.group(1))).exists():
                page.set_redirect_target(
                    self.current_page,
                    create=True,
                    summary=f"{page.title()} -> {self.current_page.title()}",
                )


if __name__ == "__main__":
    factory = GeneratorFactory()
    factory.handle_args(pwb.handle_args())
    RedirectBot(generator=factory.getCombinedGenerator(preload=True)).run()
