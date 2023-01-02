from .jobs_ import CmdJob, FuncJob, IterableJob, add_job


def rm_unnecessary_cats():
    return IterableJob(
        [
            CmdJob(
                [
                    "category",
                    "remove",
                    "-pagesonly",
                    "-batch",
                    f"-from:{c}",
                ]
            )
            for c in CmdJob(
                [
                    "listpages",
                    "-format:3",
                    "-subcatsr:角色分类",
                    "-subcatsr:内容页面",
                ]
            )
            .run(simulate=True, capture_output=True)
            .split("\n")
            if c
        ]
    )


add_job(FuncJob(rm_unnecessary_cats))
