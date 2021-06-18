import argparse
import logging

from jobs import jobs_list

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    parser = argparse.ArgumentParser(
        description='将自动化规则应用到全站条目，循环执行。',
        epilog='\n\n'.join(f'{i}\n{job}' for i, job in enumerate(jobs_list)),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        'start',
        help='从第几个任务开始执行 (default: 0)',
        type=int,
        default=0,
        choices=range(len(jobs_list)),
    )
    parser.add_argument(
        '-s',
        '--simulate',
        help='不对服务器内容做任何实际更改，只显示将更改的内容',
        action='store_true',
    )
    parser.parse_args()
