from ._jobs import CmdJob, FuncJob, IterableJob, add_job


def rm_unnecessary_cats():
    return IterableJob([
        CmdJob([
            'category',
            'remove',
            '-pagesonly',
            '-batch',
            f'-from:{c}',
        ]) for c in CmdJob([
            'listpages',
            '-format:3',
            '-subcatsr:角色',
        ]).run(True).split('\n') if c
    ])


add_job(FuncJob(rm_unnecessary_cats))
