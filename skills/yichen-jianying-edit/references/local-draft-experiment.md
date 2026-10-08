# 当前本机版本的草稿实验入口

这是独立的 opt-in 实验，不改官方入口的固定版本、应用指纹和 codec 指纹，不启用原生无界面导出。

本入口和核心必须使用相匹配的实验分支 `codex/jianying/current-draft-compat`；公开 main 的普通安装仍不包含此后端。
核心 review fork 为 `MingfeiJi/jianying-headless`，独立 Skill review fork 为 `MingfeiJi/yichen-skills`。

唯一实验配置：Apple Silicon macOS，剪映 version `11.5.13264` / build `11.6.0-beta6`，
签名 Team `X2JNK7LY8J`，安装库 SHA `e3a30819d30f008ed8fa9b147f98adb09b0b4b9dc788f599ef1bcb4901a70d0d`。
独立桥接器由公开源码在 CLT clang 17.0.0 / SDK 26.1 上编译，匹配本次实验固定 SHA；不复制官方库、不替换 canonical codec。

支持本次验证的基本主轨视频、静态 PNG、独立文字和本地音频。拒绝缓存特效、模板、花字、蒙版、复合片段及其他版本。
旧 `185.0.0` 构建格式和本机保存后的 `189.0.0` 仅在该配置被接受，未放开通用 schema 检查。

```bash
python3 CORE/tools/build_local_draft_codec.py --out CORE/work/NEW_CODEC_DIR
JIANYING_HEADLESS_ROOT=/absolute/CORE python3 SKILL/scripts/local_draft.py --codec /absolute/CORE/work/NEW_CODEC_DIR/codec-probe doctor
JIANYING_HEADLESS_ROOT=/absolute/CORE python3 SKILL/scripts/local_draft.py --codec /absolute/CORE/work/NEW_CODEC_DIR/codec-probe build --plan /absolute/plan.json --out /absolute/NEW_BUILD
JIANYING_HEADLESS_ROOT=/absolute/CORE python3 SKILL/scripts/local_draft.py --codec /absolute/CORE/work/NEW_CODEC_DIR/codec-probe publish --build /absolute/NEW_BUILD --audit /absolute/NEW_AUDIT
JIANYING_HEADLESS_ROOT=/absolute/CORE python3 SKILL/scripts/local_draft.py --codec /absolute/CORE/work/NEW_CODEC_DIR/codec-probe verify --build /absolute/NEW_BUILD --report /absolute/NEW_REPORT.json
```

`publish` 只登记本机首页，必须保存并正常退出剪映；原首页完整备份、锁、xattrs、源文件 SHA、同名拒绝覆盖和镜像核对沿用核心事务流程。
`verify` 在保存退出后运行；仍需真实打开、播放、冷重开验证。仅通过 build 或往返不算 GUI 可用。

私人素材、真实草稿、codec 二进制、运行回执均留在外部 work，不随代码发布。不同机器若工具链产物 SHA 不符，则保留构建报告并停止，禁止重写固定 SHA 通过检查。
