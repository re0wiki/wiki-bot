def ns2start(ns: str):
    return f"-start:{ns}:!"


def nss2starts(nss):
    return [ns2start(ns) for ns in nss]


ns_base = ["", "project", "template", "category", "file"]
ns_more = ns_base + ["module", "mediawiki"]
# unused
# _ns_full = ns_more + ['user', 'help']

starts_base = nss2starts(ns_base)
starts_more = nss2starts(ns_more)

if __name__ == "__main__":
    print(" ".join(starts_base))
    print(" ".join(starts_more))
