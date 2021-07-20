generator_base = (
    " -start::! -start:project:! -start:template:! -start:category:! -start:file:!"
)
generator_more = generator_base + " -start:module:! " "-start:mediawiki:!"

base: dict[str] = {
    "regex": True,
    "nocase": True,
    "exceptions": {
        "inside-tags": ["keep"],
    },
}

user_fixes = dict()

# region misc
nbsp = "\xa0"

mid_dots_code = [
    721,
    903,
    1468,
    5867,
    8226,
    8231,
    8728,
    8729,
    8901,
    9210,
    9679,
    9702,
    9899,
    10625,
    11824,
    11825,
    11827,
    12539,
    42895,
    65381,
    65793,
]
mid_dots = "[" + "".join(chr(i) for i in mid_dots_code) + "]"
mid_dot = "\xb7"

user_fixes["misc"] = base | {
    "generator": generator_base,
    "replacements": [
        (nbsp, " "),
        (mid_dots, mid_dot),
        ("－－", "——"),
        (r"<!---->|￼", ""),
        ("“", "「"),
        ("”", "」"),
        ("【", "『"),
        ("】", "』"),
        (r"(?<!==)\s*\n==", r"\n\n=="),
        (r"==\n\s*", r"==\n"),
        (r"\n{3,}", r"\n\n"),
        ("stickytable", "floatheader"),
    ],
}
# endregion

fixes: dict
# noinspection PyUnboundLocalVariable
fixes.update(user_fixes)
