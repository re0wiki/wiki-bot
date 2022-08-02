from pywikibot import family


class Family(family.Family):  # noqa: D101
    """Re0 family."""

    name = "re0"
    langs = {
        "zh": "rezero.fandom.com",
        "de": "rezero.fandom.com",
        "en": "rezero.fandom.com",
        "es": "rezero.fandom.com",
        "fr": "rezero.fandom.com",
        "it": "rezero.fandom.com",
        "ko": "rezero.fandom.com",
        "nl": "rezero.fandom.com",
        "pl": "rezero.fandom.com",
        "pt-br": "rezero.fandom.com",
        "ru": "rezero.fandom.com",
        "uk": "rezero.fandom.com",
    }

    @staticmethod
    def scriptpath(code):
        """The prefix used to locate scripts on this wiki."""
        return {
            "zh": "/zh",
            "de": "/de",
            "en": "",
            "es": "/es",
            "fr": "/fr",
            "it": "/it",
            "ko": "/ko",
            "nl": "/nl",
            "pl": "/pl",
            "pt-br": "/pt-br",
            "ru": "/ru",
            "uk": "/uk",
        }[code]

    @staticmethod
    def protocol(code):
        """The protocol to use to connect to the site."""
        return {
            "zh": "https",
            "de": "https",
            "en": "https",
            "es": "https",
            "fr": "https",
            "it": "https",
            "ko": "https",
            "nl": "https",
            "pl": "https",
            "pt-br": "https",
            "ru": "https",
            "uk": "https",
        }[code]
