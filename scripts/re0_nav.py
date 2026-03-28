from pywikibot.pagegenerators import GeneratorFactory

import pywikibot as pwb


def compile_line(line: str) -> str:
    if not line.startswith("*"):
        return ""
    prefix, stem = line.split(" ", 1)
    prefix += "*** "
    if "[" in stem:
        return prefix + stem.replace("[", "").replace("]", "")
    if "|" in stem:
        return prefix + stem
    return prefix + "|" + stem


def compile_nav(src: str) -> str:
    head = "本页面基于[[Project:Wiki-navigation]]自动生成，不应手动编辑。\n"
    content = "\n".join(c for line in src.splitlines() if (c := compile_line(line)))
    return head + content


class NavBot(pwb.bot.SingleSiteBot, pwb.bot.ExistingPageBot):
    """Compile [[Project:Wiki-navigation]]."""

    def treat_page(self) -> None:
        src = pwb.Page(self.site, "Project:Wiki-navigation").text
        self.put_current(compile_nav(src), summary="编译导航栏")


def main():
    factory = GeneratorFactory()
    args = factory.handle_args(pwb.handle_args())

    options = {}
    for arg in args:
        options[arg.removeprefix("-")] = True

    NavBot(generator=factory.getCombinedGenerator(preload=True), **options).run()


if __name__ == "__main__":
    main()
