# CKEditor 5 in ustc-course

本目录包含了 CKEditor 5 依赖的有关文件。目前编辑器版本为 40.2.0。

## 下载依赖文件

本项目使用 DLL 形式导入，因此需要下载大量 JS 文件，可以执行以下命令：

```console
wget https://unpkg.com/ckeditor5@40.2.0/build/ckeditor5-dll.js
wget https://unpkg.com/@ckeditor/ckeditor5-editor-classic@40.2.0/build/editor-classic.js
wget https://unpkg.com/@ckeditor/ckeditor5-essentials@40.2.0/build/essentials.js
wget https://unpkg.com/@ckeditor/ckeditor5-autoformat@40.2.0/build/autoformat.js
wget https://unpkg.com/@ckeditor/ckeditor5-basic-styles@40.2.0/build/basic-styles.js
wget https://unpkg.com/@ckeditor/ckeditor5-block-quote@40.2.0/build/block-quote.js
wget https://unpkg.com/@ckeditor/ckeditor5-easy-image@40.2.0/build/easy-image.js
wget https://unpkg.com/@ckeditor/ckeditor5-heading@40.2.0/build/heading.js
wget https://unpkg.com/@ckeditor/ckeditor5-image@40.2.0/build/image.js
wget https://unpkg.com/@ckeditor/ckeditor5-indent@40.2.0/build/indent.js
wget https://unpkg.com/@ckeditor/ckeditor5-link@40.2.0/build/link.js
wget https://unpkg.com/@ckeditor/ckeditor5-list@40.2.0/build/list.js
wget https://unpkg.com/@ckeditor/ckeditor5-media-embed@40.2.0/build/media-embed.js
wget https://unpkg.com/@ckeditor/ckeditor5-paste-from-office@40.2.0/build/paste-from-office.js
wget https://unpkg.com/@ckeditor/ckeditor5-table@40.2.0/build/table.js
wget https://unpkg.com/@ckeditor/ckeditor5-code-block@40.2.0/build/code-block.js
wget https://unpkg.com/@ckeditor/ckeditor5-markdown-gfm@40.2.0/build/markdown-gfm.js
wget https://unpkg.com/@ckeditor/ckeditor5-word-count@40.2.0/build/word-count.js
wget https://unpkg.com/@isaul32/ckeditor5-math@40.2.0/build/math.js
```

文件上传 (ckeditor5-file-upload) 模块使用了 https://github.com/taoky/ckeditor5-file-upload 修改后的 DLL build（位于 build 目录下），
该文件针对 40.2.0 构建，如果需要其他版本，需要下载、修改 `package.json` 后使用 `npm run dll:build` 构建。

## 样式

CSS 样式从 https://ckeditor.com/docs/ckeditor5/latest/installation/advanced/content-styles.html 取得，对于需要样式的 HTML 元素，需要添加 `ck-content` 类。

特别地，blockquote 样式的斜体字形被删除（调整为了 `normal !important`）。
