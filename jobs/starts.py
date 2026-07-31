def ns2start(ns: str):
    return f"-start:{ns}:!"


def nss2starts(nss):
    return [ns2start(ns) for ns in nss]


# ns_base/ns_more 与 user-fixes.py 的 generator_base/generator_more 是两处事实源：
# user-fixes.py 由 pywikibot/fixes.py exec（无法 import 本包），改动需两边同步。
ns_base = ["", "project", "template", "category"]
ns_more = ns_base + ["module", "mediawiki"]
# unused
_ns_full = ns_more + ["user", "help", "file"]

starts_base = nss2starts(ns_base)
starts_more = nss2starts(ns_more)

if __name__ == "__main__":
    print(" ".join(starts_base))
    print(" ".join(starts_more))
