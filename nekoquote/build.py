"""语录月表构建器：lua_base 解析 → 时间戳归月 → raw 推合流 → 月表 emit。

字段保真策略：每条目字段保存 (name, quote, raw_content) 原样三元组，重放零变换；
仅新推文条目用双引号 + 自有转义。
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
EPOCH = 1288834974657

ENTRY_RE = re.compile(r"\{\s*src\s*=.*?\n\s*\}", re.DOTALL)
FIELD_RE = re.compile(r"(\w+)\s*=\s*(['\"])((?:\\.|(?!\2).)*?)\2", re.DOTALL)
STATUS_RE = re.compile(r"(?:twitter|x)\.com/nezumiironyanko/status/(\d+)")
DATE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
DATE_CN = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})")


def snowflake_jst(tid):
    ms = (int(tid) >> 22) + EPOCH
    return datetime.fromtimestamp(ms / 1000, JST)


def parse_table(lua):
    """返回 [(fields=[(name,quote,raw)], block_text)]。"""
    out = []
    for bm in ENTRY_RE.finditer(lua):
        fields = [
            (f.group(1), f.group(2), f.group(3)) for f in FIELD_RE.finditer(bm.group(0))
        ]
        out.append((fields, bm.group(0)))
    return out


def fget(fields, name):
    for n, q, r in fields:
        if n == name:
            return r
    return None


def derive_date(fields, src_table):
    """返回 (yyyy-mm, sort_key, note)。note 非空 = 特殊处置说明。"""
    src = fget(fields, "src") or ""
    m = STATUS_RE.search(src)
    if not m:
        # 推链接可能在内容字段的 ref 里（罗兹瓦尔 FreeTalk 8 条）
        for n, q, r in fields:
            if n == "src":
                continue
            m = STATUS_RE.search(r)
            if m:
                break
    if m:
        dt = snowflake_jst(m.group(1))
        return dt.strftime("%Y-%m"), dt, ""
    m = DATE_ISO.search(src)
    if m:
        return (
            f"{m.group(1)}-{m.group(2)}",
            datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=JST),
            "",
        )
    m = DATE_CN.search(src)
    if m and "～" not in src:
        return f"{m.group(1)}-{int(m.group(2)):02d}", None, ""
    if "爱蜜莉雅2017生日会" in src:
        return "2017-09", None, "生日会语义定月"
    if "早期ask" in src:
        return (
            "2014-09",
            None,
            "ask 孤儿/抄录→2014-09 兜底",
        )  # 抄录的精确继承在合并阶段做
    return None, None, "!!无日期"


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def emit_entry(fields):
    """fields: [(name, quote, raw)] → lua 条目文本（四空格缩进风格）。"""
    lines = ["    {"]
    for n, q, r in fields:
        lines.append(f"      {n} = {q}{r}{q},")
    lines.append("    },")
    return "\n".join(lines)


def emit_table(entries):
    """月表 lua 全文。"""
    body = "\n".join(emit_entry(e["fields"]) for e in entries)
    return f"local p = {{}}\n\np.list = {{\n{body}\n}}\n\nreturn p\n"


MAIN = r"""local p = {}

local getArgs = require('Dev:Arguments').getArgs

-- 月表 2010-01 起至当前月（UTC），程序化生成不手列；页面尚未建立的月份 pcall 跳过
local data_names = {}
do
    local y1 = tonumber(os.date('!%Y'))
    local m1 = tonumber(os.date('!%m'))
    for y = 2010, y1 do
        for m = 1, 12 do
            if y < y1 or m <= m1 then
                data_names[#data_names + 1] = ('%d-%02d'):format(y, m)
            end
        end
    end
end

local function iter_sources(table_filter)
    local names = data_names
    if table_filter then
        names = {}
        for _, name in ipairs(data_names) do
            if name == table_filter then
                names = { name }
                break
            end
        end
    end
    local i = 0
    return function()
        while true do
            i = i + 1
            local name = names[i]
            if not name then
                return
            end
            local ok, mod = pcall(require, 'Module:NekoQuote/' .. name)
            if ok then
                return mod
            end
        end
    end
end

local function any_in(targets, s)
    if not targets[1] then
        return true
    end
    for _, target in ipairs(targets) do
        if mw.ustring.find(s, target, 1, true) then
            return true
        end
    end
    return false
end

local function content_html(prefix, zh, ja)
    local first
    local rest = {}
    for _, content in ipairs { zh, ja } do
        if content ~= '' then
            if first then
                table.insert(rest, content)
            else
                first = content
            end
        end
    end
    if not first then
        return ''
    end
    if prefix then
        first = ("'''%s'''：%s"):format(prefix, first)
    end
    if not rest[1] then
        return '<br/>' .. first
    end
    return '<br/><div class="wds-dropdown ruby-tooltip"><div class="wds-dropdown__toggle">'
        .. first
        .. '</div><div class="wds-dropdown__content">'
        .. table.concat(rest, '<hr/>')
        .. '</div></div>'
end

---@param targets table
---@param frame table
function p._query(targets, frame, table_filter)
    local buf = {}
    local cnt = 0

    for source in iter_sources(table_filter) do
        for _, data in ipairs(source.list) do
            local src = data.src

            local t = data.t or ''
            local jt = data.jt or ''

            local q = data.q or ''
            local jq = data.jq or ''

            if any_in(targets, src
                    .. t .. jt
                    .. q .. jq) then
                cnt = cnt + 1
                buf[cnt] = '<li><small>' .. src .. '</small>'
                    .. content_html('Q', q, jq)
                    .. content_html(q ~= '' and 'A' or nil, t, jt)
                    .. '</li>'
            end
        end
    end

    if cnt == 0 then
        return '『[[模块:NekoQuote]] 查询结果为空』[[分类:模块:NekoQuote 查询结果为空]]'
    end
    return frame:preprocess('<ol>' .. table.concat(buf) .. '</ol>')
end

function p.query(frame)
    local args = getArgs(frame)
    local table_filter = args['table']
    args['table'] = nil
    return p._query(args, frame, table_filter)
end

return p
"""


def emit_main(months):
    Path("logs/nekoquote/main.lua").write_text(MAIN, encoding="utf-8")


def strip_tco(s):
    # Fandom 垃圾信息过滤器禁 t.co 短链（封禁ID #855849）——推文尾链/媒体链直接剥除；
    # youtu.be 同属短链黑名单，机械展开为完整 youtube URL（无需请求）
    s = re.sub(r"https?://youtu\.be/(\S+)", r"https://www.youtube.com/watch?v=\1", s)
    return re.sub(r"\s*https?://(?:t\.co|a\.co)/\S+", "", s).strip()


EP_MARKS = (
    json.loads(Path("logs/nekoquote/ep_marks.json").read_text(encoding="utf-8"))
    if Path("logs/nekoquote/ep_marks.json").exists()
    else {}
)


def raw_tweet_entry(tid, rec, q_text):
    dt = snowflake_jst(tid)
    url = f"https://twitter.com/nezumiironyanko/status/{tid}"
    mark = EP_MARKS.get(tid)
    src = f"{dt.strftime('%Y-%m-%d')}{' ' + mark if mark else ''} [{url} 原推]"
    fields = [("src", '"', esc(src))]
    if q_text:
        q_clean = re.sub(r"^(@\w+\s*)+", "", q_text).strip()
        q_clean = re.sub(r"\s*\r?\n\s*", "<br/>", q_clean)
        fields.append(("jq", '"', esc(strip_tco(q_clean))))
    ja = re.sub(r"\s*\r?\n\s*", "<br/>", strip_tco(rec["text"].strip()))
    fields.append(("jt", '"', esc(ja)))
    return {"fields": fields, "key": dt, "from": "raw", "note": ""}


def merge_raw(buckets, existing_ids):
    """合流新推（id 级去重）。返回新增条数。中文译文从 logs/nekoquote/zh.json 回填（a/q 字段）。"""
    tw = json.loads(Path("logs/nekoquote/tweets.json").read_text(encoding="utf-8"))
    zh_map = (
        json.loads(Path("logs/nekoquote/zh.json").read_text(encoding="utf-8"))
        if Path("logs/nekoquote/zh.json").exists()
        else {}
    )
    n = 0
    for tid, rec in tw.items():
        if rec.get("author") != "nezumiironyanko" or tid in existing_ids:
            continue
        e = raw_tweet_entry(tid, rec, None)
        month = e["key"].strftime("%Y-%m")
        if not ("2010-01" <= month <= "2026-12"):
            print(f"  !! 越界月份 {month}（脏 id {tid}），跳过")
            continue
        # jq：提问推正文（若已抓到）+ 其中文（若已译）
        qid = rec.get("reply_to")
        if qid and qid in tw and tw[qid].get("author") != "nezumiironyanko":
            q_clean = re.sub(r"^(@\w+\s*)+", "", tw[qid]["text"]).strip()
            q_clean = re.sub(r"\s*\r?\n\s*", "<br/>", q_clean)
            e["fields"].insert(1, ("jq", '"', esc(strip_tco(q_clean))))
            qzh = zh_map.get(qid, {}).get("qzh")
            if qzh:
                e["fields"].insert(1, ("q", '"', esc(qzh)))
        zh = zh_map.get(tid, {}).get("zh")
        if zh:
            e["fields"].append(("t", '"', esc(zh)))
            # 机翻署名
            e["fields"][0] = ("src", '"', esc(e["fields"][0][2] + " · 译：Kimi K3"))
        buckets.setdefault(month, []).append(e)
        n += 1
    return n


def main():
    # 数据源：本地基线 logs/nekoquote/lua_base（旧主题表已在切流中删除，wiki 上的唯一副本就是月表）
    buckets = {}
    problems = []
    existing_ids = set()
    total = 0
    for f in sorted(Path("logs/nekoquote/lua_base").glob("*.lua")):
        for fields, block in parse_table(f.read_text(encoding="utf-8")):
            total += 1
            src = fget(fields, "src") or ""
            existing_ids.update(STATUS_RE.findall(src))
            month, key, note = derive_date(fields, f.stem)
            if month is None and "第12集" in src:
                # 由里乌斯表实况抄录：同一推文不同措辞（实况表对应条目 2016-06-26，人工核定）
                month, note = "2016-06", "实况抄录语义归月"
            if month is None:
                # lua_base 条目：文件名即正确月份（首建已验证放置），编者注等无日期条目直接继承
                month, note = f.stem, "基线月继承"
            buckets.setdefault(month, []).append(
                {"fields": fields, "key": key, "from": f.stem, "note": note}
            )

    print(
        f"解析 {total} 条，入桶 {sum(len(v) for v in buckets.values())}，问题 {len(problems)}，既有推 id {len(existing_ids)}"
    )

    n_raw = merge_raw(buckets, existing_ids)
    print(f"合流新推 {n_raw} 条")

    outdir = Path("logs/nekoquote/lua")
    outdir.mkdir(parents=True, exist_ok=True)
    for month, entries in sorted(buckets.items()):
        # 排序：有时间键的按时刻，无键的（日期精度）排当日最前
        entries.sort(
            key=lambda e: (
                (e["key"] or datetime(1, 1, 1, tzinfo=JST)).strftime("%Y-%m-%d %H:%M")
                if e["key"]
                else e["fields"][0][2][:10]
            )
        )
        (outdir / f"{month}.lua").write_text(emit_table(entries), encoding="utf-8")
    emit_main(buckets.keys())
    print(f"emit {len(buckets)} 张月表 → {outdir}，主模块 → logs/nekoquote/main.lua")


if __name__ == "__main__":
    main()
