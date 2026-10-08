# 独立 beta6 草稿实验

本次从公开 `jianying-headless` commit `42b3d75b15bd9f3a9bb4c11b2f5205f7b4312252`
和 `yichen-skills` commit `9bd78982aa75aa179258bc9009fe4dcf2f2973b9` 重新检出。
canonical 的 `11.5.0` / `11.4.2` 应用、codec、IO manifest、资源与 export profiles 均未放宽。

当前已签名安装的精确 version `11.5.13264`、build `11.6.0-beta6` 不属于 canonical 发行配置。
新增入口只建立一个明确选择的草稿实验，不将一个相近版本推断为兼容。

| 证据 | 本次观测 |
| --- | --- |
| 官方应用签名 | deep/strict 通过，Team `X2JNK7LY8J` |
| 安装库 SHA256 | `e3a30819d30f008ed8fa9b147f98adb09b0b4b9dc788f599ef1bcb4901a70d0d` |
| 桥接源码 | 原 C++、EncryptUtil.h 和 runtime_io.py 字节与公开 manifest 一致 |
| 本机工具链 | Apple clang 17.0.0 (clang-1700.4.4.1)，SDK 26.1，arm64，min macOS 26.0 |
| 独立 codec SHA256 | `57eab54b180f37b45278dff33d02528d587e366df824aae0734360140acbe138`；四次隔离编译字节一致，含两次源码包解开到新目录 |
| 旧实际草稿副本 | 30.9s / 9轨 / schema 189.0.0 / 保存平台 beta3；解密、加密再解密原文一致，原件 SHA 不变 |
| 本机新草稿副本 | 39.2s / schema 189.0.0 / 保存平台 beta6；相同往返通过 |
| 中文和 emoji | 独立 JSON pipe 往返通过 |
| 2s 新建草稿 | 构建、首页登记、原生打开播放、保存退出及结构回读通过；185.0.0 保存为 189.0.0 |
| 50s 多轨案例 | 10轨、74段、12个媒体依赖、1个本地字体；初版原生完整打开与多个实际画面检查通过 |
| 排版修正后的交付候选 | 通过独立 Skill 入口构建与登记；build 6.266s，publish 20.764s；最终 GUI 冷重开尚待分项补验 |
| 独立源码包三轨小样 | H.264、中文/emoji 文本与本地 WAV；通过 Skill doctor/build/verify-build，build 7.473s；GUI 待验 |
| 完整案例源码包重建 | 新源码目录和素材路径，10轨/74段/50s；归一化计划、12个媒体及字体 SHA 与交付版相同，主画面无空档；build 4.748s |
| 五项拒绝场景 | 改源码、改 codec、缓存蒙版、export 和主程序未退出均拒绝；未退出的登记调用未改变首页 SHA，目标/audit 未创建 |

草稿流程不调用原生导出 ABI。`local_draft_runtime` 拒绝缓存效果/模板/复合片段，且 canonical
`EXPORT_PROFILES` 仍拒绝此 profile。只验证本次使用的 H.264、PNG、WAV、普通原生文字与独立 TTF。
已保存的 189.0.0 必须同时声明精确 beta6 保存平台；旧 beta3 样本仅作只读 codec 对照，未获编辑配置。

`jy14_headless` 的新可选 `runtime_provider` 与 `schema_validator` 显式传入依赖；默认仍为原 canonical
模块。build、publish、verify 使用相同 provider，并保留原首页快照、目录独占锁、编辑器关闭检查、
同名拒绝覆盖、xattrs、媒体与字体 SHA、四镜像独立 inode 和完整结构比较。没有 monkey patch canonical
运行常量或给导出设置伪造 profile。Skill 的源码 pin 因 API 修改而重新核验，原运行版本与 codec pin 不变。

复现命令与限定入口见 [Skill 本机实验](../skills/yichen-jianying-edit/references/local-draft-experiment.md)。
直接执行 `tools/build_local_draft_codec.py --out work/NEW_DIR` 只写新目录。工具链、app tuple、source 或
产物 SHA 不符时留存报告并停止，不重写固定指纹。`tools/local_draft.py` 必须显式指定该 codec。

真实媒体、草稿、账号材料、codec 二进制和私人运行证据保留在外部 work，不随源码/PR发布。
通过结构验证不等同于完整主观视听验收或内容传播效果。final GUI 与冷重开状态需后续分项记录。

## 经验包重放

`tools/replay_local_draft_package.py --package-dir /ABS/PACKAGE` 提供 unpack、compile、build、publish 和
verify。它读取外部经验包的锁定源码归档与输入 manifest；不能用无媒体的源码 checkout 代替外部包。
归档摘要检查后仍拒绝链接及路径逃逸；每阶段使用新目录，保存实际命令、stdout/stderr、退出码和耗时。
build 依次调用独立 Skill 的 doctor/build/verify-build，基础素材已准备好之后才开始计时。
GUI 打开、连续播放、保存及冷重开必须另行观察；脚本不会自动填写 GUI 通过标记。

本次经验包冻结核心执行源码 `b8f0c71a53b86a59655a70de389b2f425be8e834` 和独立 Skill
`83e66319299b64792634354f5f040ebc07ec5ea6`。包的重放器文件单独记录 SHA；后续文档/重放器提交
不代表核心运行组件改变。示例资产、字体、应用库不提交到公开仓库。
