# 图片原图下载实测记录

本文保存图片下载方案的实测证据；当前执行规则见 `../SKILL.md` 的「图片原图下载」节。

## static CDN 403 与客户端对照（2026-11-02）

- `static.wikia.nocookie.net` 间歇返回 **HTTP 403 + `Cf-Mitigated: challenge`**，
  正文是挑战 HTML，不是图片。同一 URL 可在三张连续失败后于稍后恢复 200；
  正式任务中 static + curl 浏览器头曾三张全部失败，后续密集及分时测试又全部成功，
  因此不能据单次成功认定方案稳定。
- 只换浏览器 UA、给 pywikibot `http.fetch` 补 `Sec-Fetch` 均无效；系统 curl 补浏览器头
  仍间歇失败。`curl_cffi` 0.17.0 一次返回 200 后连续返回 403，也不稳定。
- `images.wikia.com` 使用相同路径与 `format=original`。默认 curl 与默认 pywikibot
  在 10 轮密集 + 5 轮每分钟对照中均 **15/15** 返回正确原图；三张实际待同步 PNG
  亦逐张校验 SHA-1 一致。实现保留原 `FilePage.download()` 的 25×读限速与 SHA-1 校验。
- `vignette.wikia.nocookie.net` 的默认客户端表现与 static 相同，没有收益。
- 全新 headless Edge 等 30 秒仍未通过挑战；headful Edge 能取到原图且 SHA-1 一致，
  但需要可见浏览器，不适合作为当前常驻方案。

## 其他入口

- `Special:FilePath` / `Special:Redirect/file` 最终返回 WebP，不是原图。
- 文件页 `?action=download` 跳至文章 HTML；`Special:Download` 返回 404。
- URL 服务端上传仍被站点禁用：账号虽有 `upload_by_url` 权限且 `action=upload`
  暴露 `url` 参数，实际提交仍返回 `copyuploaddisabled: Upload by URL disabled.`。
  权限与 API 参数存在不代表功能可用。

## 元数据边界

抽样 JPG 时 static/images/vignette 三处返回字节完全相同，但均与 API
`latest_file_info` 的大小/SHA-1 不同（2026-11-02 实测）。因此响应与元数据不一致不能
归因于 images 别名；既有 SHA-1 校验会拒绝此类内容，不应为绕过失败而删除校验。
