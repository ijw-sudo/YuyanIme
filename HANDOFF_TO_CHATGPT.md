# YuyanIme 项目交接说明

## 仓库结构

这是一个 Android 输入法项目，采用主仓库 + git 子模块架构：

| 仓库 | 地址 | 分支 | 用途 |
|------|------|------|------|
| 主仓库 | `github.com/ijw-sudo/YuyanIme` | `master` | 构建配置、CI/CD、子模块指针 |
| 子模块 | `github.com/ijw-sudo/yuyansdk` | `lite-trim` | 输入法 SDK 核心代码 |

子模块在主仓库的 `yuyansdk/` 目录下。**你的工作目录是 yuyansdk 子模块。**

## 当前分支状态

- **yuyansdk 子模块**在分支 `lite-trim` 上（已推送到 origin）
- **主仓库**在分支 `master` 上（已推送到 origin2）
- 主仓库的 `origin` 指向上游 `gurecn/YuyanIme`，`origin2` 指向 fork `ijw-sudo/YuyanIme`。推送用 origin2。

## 提交子模块代码的流程

```
cd yuyansdk
git add -A
git commit -m "你的提交信息"
git push origin lite-trim

cd ..
git add yuyansdk
git commit -m "update submodule: 简短说明"
git push origin2 master
```

**必须先推送子模块，再更新主仓库的指针**，否则 CI 拉不到新代码。

## CI / 构建

- 推送到主仓库 master 会触发 GitHub Actions（`.github/workflows/build.yml`）
- 构建产物（APK）在 Actions 页面的 Artifacts 里下载
- 无签名配置时只出 debug APK
- `app/build.gradle` 中 signing configs 已恢复，会用环境变量或本地 keystore.properties 文件

## 已完成的功能和最近改动

### AI 翻译功能（本次改动最核心的新功能）

**文件清单：**
- `yuyansdk/src/main/java/com/yuyan/inputmethod/translation/AITranslationClient.kt` — HTTP 客户端，调 DeepSeek API
- `yuyansdk/src/main/java/com/yuyan/inputmethod/translation/AITranslationState.kt` — 状态枚举：IDLE / TRANSLATING / TRANSLATED / FAILED
- `yuyansdk/src/main/java/com/yuyan/imemodule/keyboard/InputView.kt` — 翻译触发逻辑（`triggerTranslation()`、`shouldShowTranslateButton()`、`resetTranslationState()`）
- `yuyansdk/src/main/java/com/yuyan/imemodule/keyboard/TextKeyboard.kt` — Enter 键状态更新
- `yuyansdk/src/main/java/com/yuyan/imemodule/utils/KeyboardLoaderUtil.kt` — 添加了 `ToggleState("发送", 12)`
- `yuyansdk/src/main/java/com/yuyan/imemodule/prefs/AppPrefs.kt` — 默认模型改为 `deepseek-v4-flash`
- `yuyansdk/src/main/java/com/yuyan/imemodule/ui/fragment/TranslationSettingsFragment.kt` — 设置页，默认模型 `deepseek-v4-flash`
- `yuyansdk/src/main/AndroidManifest.xml` — 添加了 INTERNET 权限
- `yuyansdk/src/main/java/com/yuyan/imemodule/application/CustomConstant.kt` — 已添加 `YUYAN_IME_REPO` 等常量

**翻译工作流程：**
1. 用户在中文输入状态下打字
2. 输入法检测：中文模式 + 无正在输入的拼音 + 光标前有文字 → Enter 键显示"翻译"
3. 点"翻译"→ 显示"翻译中"→ 取光标前最后一段文本 → POST 到 DeepSeek API
4. 成功的翻译结果替换原文 → 状态变为 TRANSLATED → Enter 键显示"发送"
5. 用户点"发送"或移动光标重置为 IDLE

**SettingsActivity 导航修复：**
- `yuyansdk/src/main/java/com/yuyan/imemodule/utils/AppUtil.kt` — `launchMainToDest()` 改用直接 `startActivity<SettingsActivity>` + extras (`nav_destination`)
- `yuyansdk/src/main/java/com/yuyan/imemodule/ui/activity/SettingsActivity.kt` — `onCreate` 中读取 `nav_destination` extra，自动导航到目标 fragment

### 顿号 (、) 添加到默认标点列表

- `yuyansdk/src/main/java/com/yuyan/imemodule/database/DataBaseKT.kt`
  - `initDb()` 的 symbolPinyin 列表里加入了 `、`
  - 添加了 `MIGRATION_4_5`，对旧用户执行 `INSERT OR IGNORE`

### Lite 精简（本次改动，lite-trim 分支）

删除了以下内容以减小 APK 体积（约减少 50MB）：

| 删除内容 | 涉及文件 |
|----------|----------|
| 手写输入模型 `assets/hw/`（8.1MB） | 删除整个目录 |
| 五笔/笔画输入 `assets/rime/build/stroke.*`（41.5MB） | 删除 `.table.bin`, `.prism.bin`, `.schema.yaml` |
| 不用的双拼方案（abc/natural/mspy/sogou/ziguang/ls17） | 删除对应 `double_pinyin_*` 文件 |
| 键盘切换界面去掉了手写/笔画/LX17 选项 | `SettingsContainer.kt` |
| 工具栏菜单去掉了 OneHanded / FloatKeyboard / FlowerTypeface | `SkbFunData.kt`, `DataBaseKT.kt` |
| 键盘类型映射中将手写/LX17 回退到 T9 | `KeyboardManager.kt` |
| 数据库迁移 v5→v6：清理旧用户残留的已删除菜单项 | `DataBaseKT.kt` |

**保留的输入方案：** T9 拼音、QWERTY 全键拼音、小鹤双拼(FlyPy)、英文、数字键盘、文本编辑键盘

**保留的剩余资产：** `assets/rime/` 71MB（pinyin.table.bin 65MB 是核心词库），`assets/pinyindb/` 564KB

## 已知未完成 / 待解决

### 1. 设置按钮不响应（已知 Bug，未修复）

**问题：** T9 键盘左侧标点栏底部的齿轮图标点不动。

已经尝试了 3 种方案都没成功 — 把 context 改成 Application、把 NavDeepLinkBuilder 换成直接 startActivity、把点击事件从 ImageView 移到父 LinearLayout。目前保持最后一个方案的状态（点击在 LinearLayout 上，ImageView 设为不可点击），但实际仍不工作。可能在 RecyclerView footer 里有其他触摸事件拦截。

相关文件：
- `yuyansdk/src/main/java/com/yuyan/imemodule/keyboard/container/T9TextContainer.kt`（`mLlAddSymbol`）
- `yuyansdk/src/main/java/com/yuyan/imemodule/keyboard/container/HandwritingContainer.kt`（同上模式）
- `yuyansdk/src/main/java/com/yuyan/imemodule/keyboard/container/CandidatesContainer.kt`（同上模式）
- `yuyansdk/src/main/java/com/yuyan/imemodule/utils/AppUtil.kt`（`launchSettingsToPrefix()`）

### 2. Lite 精简未深入的部分（对 APK 体积影响很小，低于 1MB）

这些功能删不删对 APK 大小的区别微乎其微，主要是代码层面的整洁度：

- 微信 Emoji 和颜文字(kaomoji)数据 → `EmojiconData.kt` 第 65-81 行的 `wechatEmojiconData`
- 花漾字功能 → `data/flower/` 目录
- 自定义主题（目前有 14 个内置主题和自定义主题系统）→ `data/theme/` 目录
- 键盘风格（Google/Samsung/Yuyan 三种）→ `SkbStyleMode.kt`
- 部分 SettingsFragment（手写设置、语音设置等对应的代码还在）

**不建议删**这些代码，因为：
- 它们不占 APK 安装体积（只占几十 KB 源码）
- 删除引入的风险比收益大（容易破坏现有功能）
- R8/ProGuard 不引用的代码本来就不会打进 APK

### 3. 其他注意事项

- `DataBaseKT.kt` 的 `@Database` version 现在=6，migration 链从 1→2→3→4→5→6 完整
- `pinyin.table.bin` 是 65MB，包含了全部拼音词库，不能动
- 子模块里还有 `HandwritingKeyboard.kt` 和 `HWEngine.kt` 等死代码没删，但它们在 UI 上已不可达，不影响功能
- `SettingsContainer.kt` 的 `showSkbSelelctModeView()` 硬编码了小鹤双拼的 `R.string.double_pinyin_flypy_plus`，双拼设置还剩 flypy 一种

## 在你动手之前

1. 确认你在 `yuyansdk/` 目录下，当前分支是 `lite-trim`
2. 如果 `git pull origin lite-trim` 有冲突，以 remote 为准
3. 修改完子模块后记得：先 push 子模块，再 cd 到主仓库 `git add yuyansdk && git commit && git push origin2 master`
4. CI 触发后大约 5-6 分钟出 APK，在 GitHub Actions 页面下载
