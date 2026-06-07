#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / "yuyansdk"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print(f"patched {path.relative_to(ROOT)}")


def replace_required(text: str, old: str, new: str, name: str) -> str:
    if old not in text:
        raise SystemExit(f"missing pattern: {name}")
    return text.replace(old, new, 1)


def patch_symbol_container() -> None:
    path = SDK / "src/main/java/com/yuyan/imemodule/keyboard/container/SymbolContainer.kt"
    text = read(path)

    if "import android.view.View" not in text:
        text = text.replace("import android.view.MotionEvent\n", "import android.view.MotionEvent\nimport android.view.View\n", 1)
    if "import com.yuyan.imemodule.manager.InputModeSwitcher" not in text:
        text = text.replace("import com.yuyan.imemodule.keyboard.KeyboardManager\n", "import com.yuyan.imemodule.keyboard.KeyboardManager\nimport com.yuyan.imemodule.manager.InputModeSwitcher\n", 1)

    if "private val chinesePunctuation" not in text:
        marker = "    private var mHandler: Handler? = null\n"
        data = """    private var mHandler: Handler? = null
    private val chinesePunctuation = listOf(
        "，", "。", "？", "！", "、", "；", "：", "“", "”", "‘", "’",
        "（", "）", "《", "》", "……", "——", "·", "￥", "@", "#"
    )
    private val englishPunctuation = listOf(
        ",", ".", "?", "!", "'", "\"", ";", ":", "(", ")", "-", "_",
        "/", "@", "#", "&", "*", "+", "=", "...", "\$"
    )
"""
        text = replace_required(text, marker, data, "punctuation lists")

    old = """    fun setSymbolsView() {
        mShowType = SymbolMode.Symbol
        isLockSymbol = false   // 符号键默认未锁定，表情键盘默认锁定
        ivDelete.setImageResource(R.drawable.icon_symbol_lock)
        ivDelete.drawable.setTint(activeTheme.keyTextColor)
        val mSymbolsEmoji = EmojiconData.symbolData
        mVPSymbolsView.adapter = SymbolPagerAdapter(context, mSymbolsEmoji, mShowType){ symbol, _ ->
            onItemClickOperate(symbol)
        }
        val data = mSymbolsEmoji.keys.toList()
        TabLayoutMediator(tabLayout, mVPSymbolsView) { tab, position ->
            tab.view.background = null
            tab.setCustomView(ImageView(context).apply {
                setImageDrawable(ContextCompat.getDrawable(context,data[position]).apply {
                    this?.setTint(activeTheme.keyTextColor)
                })
            })
            tab.view.setPadding(dp(5))
        }.attach()
        mVPSymbolsView.currentItem = 0
    }"""
    new = """    fun setSymbolsView() {
        mShowType = SymbolMode.Symbol
        isLockSymbol = false
        tabLayout.visibility = View.GONE
        ivDelete.setImageResource(R.drawable.icon_symbol_lock)
        ivDelete.drawable.setTint(activeTheme.keyTextColor)
        val symbols = if (InputModeSwitcher.isEnglish) englishPunctuation else chinesePunctuation
        val mSymbolsEmoji = linkedMapOf(R.drawable.icon_symbol_chinese to symbols)
        mVPSymbolsView.adapter = SymbolPagerAdapter(context, mSymbolsEmoji, mShowType){ symbol, _ ->
            onItemClickOperate(symbol)
        }
        mVPSymbolsView.currentItem = 0
    }"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "val mSymbolsEmoji = linkedMapOf(R.drawable.icon_symbol_chinese to symbols)" not in text:
        text = re.sub(
            r"    fun setSymbolsView\(\) \{.*?\n    \}\n\n    /\*\*\n     \* 切换显示界面",
            new + "\n\n    /**\n     * 切换显示界面",
            text,
            count=1,
            flags=re.S,
        )

    if "fun setEmojisView" in text and "tabLayout.visibility = View.VISIBLE" not in text:
        text = text.replace(
            "    fun setEmojisView(showType: SymbolMode) {\n        mShowType = showType",
            "    fun setEmojisView(showType: SymbolMode) {\n        tabLayout.visibility = View.VISIBLE\n        mShowType = showType",
            1,
        )

    write(path, text)


if __name__ == "__main__":
    if not SDK.exists():
        raise SystemExit("yuyansdk submodule is missing")
    patch_symbol_container()
