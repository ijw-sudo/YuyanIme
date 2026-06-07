#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / 'yuyansdk'


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')
    print('patched', path.relative_to(ROOT))


def replace_required(text: str, old: str, new: str, name: str) -> str:
    if old not in text:
        raise SystemExit('missing pattern: ' + name)
    return text.replace(old, new, 1)


def kotlin_quote(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$') + '"'


def kotlin_list(name: str, values):
    items = [kotlin_quote(v) for v in values]
    lines = ['    private val ' + name + ' = listOf(']
    for index in range(0, len(items), 10):
        suffix = ',' if index + 10 < len(items) else ''
        lines.append('        ' + ', '.join(items[index:index + 10]) + suffix)
    lines.append('    )')
    return '\n'.join(lines)


def replace_function(text: str, name: str, new_body: str) -> str:
    start = text.find('    fun ' + name + '(')
    if start < 0:
        raise SystemExit('missing function: ' + name)
    next_doc = text.find('    /**', start + 1)
    if next_doc < 0:
        raise SystemExit('missing end for function: ' + name)
    return text[:start] + new_body + '\n\n' + text[next_doc:]


def patch_symbol_container() -> None:
    path = SDK / 'src/main/java/com/yuyan/imemodule/keyboard/container/SymbolContainer.kt'
    text = read(path)
    if 'fun showBasicSymbolsPage()' in text and 'fun showMoreSymbolsPage()' in text:
        write(path, text)
        return

    if 'import android.view.View' not in text:
        text = text.replace('import android.view.MotionEvent\n', 'import android.view.MotionEvent\nimport android.view.View\n', 1)
    if 'import com.yuyan.imemodule.manager.InputModeSwitcher' not in text:
        text = text.replace('import com.yuyan.imemodule.keyboard.KeyboardManager\n', 'import com.yuyan.imemodule.keyboard.KeyboardManager\nimport com.yuyan.imemodule.manager.InputModeSwitcher\n', 1)

    if 'private val chinesePunctuationPage1' not in text:
        marker = '    private var mHandler: Handler? = null\n'
        chinese_page_1 = ['，', '。', '？', '！', '、', '；', '：', '“', '”', '#+=', '‘', '’', '（', '）', '《', '》', '……', '——', '·', '￥']
        chinese_page_2 = ['【', '】', '「', '」', '『', '』', '〈', '〉', '〔', '123', '～', '｜', '／', '％', '※', '＠', '＃', '＆', '＊', '〃']
        english_page_1 = [',', '.', '?', '!', "'", '"', ';', ':', '(', '#+=', ')', '-', '_', '/', '@', '#', '&', '*', '+', '=']
        english_page_2 = ['[', ']', '{', '}', '<', '>', '\\', '|', '~', '123', '`', '^', '%', '$', '€', '£', '¥', '©', '®', '™']
        data = marker + kotlin_list('chinesePunctuationPage1', chinese_page_1) + '\n' + kotlin_list('chinesePunctuationPage2', chinese_page_2) + '\n' + kotlin_list('englishPunctuationPage1', english_page_1) + '\n' + kotlin_list('englishPunctuationPage2', english_page_2) + '\n'
        text = replace_required(text, marker, data, 'punctuation page lists')

    if 'result == "#+="' not in text:
        text = replace_required(text, '        val softKey = SoftKey(label = result)\n', '        if (mShowType == SymbolMode.Symbol) {\n            if (result == "#+=") {\n                mVPSymbolsView.currentItem = 1\n                return\n            }\n            if (result == "123") {\n                mVPSymbolsView.currentItem = 0\n                return\n            }\n        }\n        val softKey = SoftKey(label = result)\n', 'symbol page switch handling')

    new_set_symbols = '''    fun setSymbolsView() {
        mShowType = SymbolMode.Symbol
        isLockSymbol = false
        tabLayout.visibility = View.GONE
        ivDelete.setImageResource(R.drawable.icon_symbol_lock)
        ivDelete.drawable.setTint(activeTheme.keyTextColor)
        val firstPage = if (InputModeSwitcher.isEnglish) englishPunctuationPage1 else chinesePunctuationPage1
        val secondPage = if (InputModeSwitcher.isEnglish) englishPunctuationPage2 else chinesePunctuationPage2
        val mSymbolsEmoji = linkedMapOf(
            R.drawable.icon_symbol_chinese to firstPage,
            R.drawable.icon_symbol_english to secondPage
        )
        mVPSymbolsView.adapter = SymbolPagerAdapter(context, mSymbolsEmoji, mShowType){ symbol, _ ->
            onItemClickOperate(symbol)
        }
        mVPSymbolsView.currentItem = 0
    }'''
    text = replace_function(text, 'setSymbolsView', new_set_symbols)

    if 'tabLayout.visibility = View.VISIBLE' not in text:
        text = text.replace('    fun setEmojisView(showType: SymbolMode) {\n        mShowType = showType', '    fun setEmojisView(showType: SymbolMode) {\n        tabLayout.visibility = View.VISIBLE\n        mShowType = showType', 1)

    write(path, text)


def patch_symbol_adapter() -> None:
    path = SDK / 'src/main/java/com/yuyan/imemodule/adapter/SymbolAdapter.kt'
    text = read(path)
    if 'fun showBasicSymbolsPage()' in read(SDK / 'src/main/java/com/yuyan/imemodule/keyboard/container/SymbolContainer.kt'):
        write(path, text)
        return

    if 'import android.graphics.drawable.GradientDrawable' not in text:
        text = text.replace('import android.content.Context\n', 'import android.content.Context\nimport android.graphics.drawable.GradientDrawable\n', 1)

    start = text.find('        holder.textView.text = data')
    end = text.find('        holder.textView.setOnClickListener', start)
    if start < 0 or end < 0:
        raise SystemExit('missing SymbolAdapter binding block')
    new_block = '''        holder.textView.text = data
        if (viewType == SymbolMode.Symbol) {
            val margin = holder.itemView.dp(3)
            val keyWidth = ((EnvironmentSingleton.instance.skbWidth - holder.itemView.dp(72)) / 10)
                .coerceAtLeast(holder.itemView.dp(26))
            val params = (holder.itemView.layoutParams as? FlexboxLayoutManager.LayoutParams)
                ?: FlexboxLayoutManager.LayoutParams(keyWidth, holder.itemView.dp(42))
            params.width = keyWidth
            params.height = holder.itemView.dp(42)
            params.setMargins(margin, margin, margin, margin)
            holder.itemView.layoutParams = params
            holder.itemView.background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = holder.itemView.dp(7).toFloat()
                setColor(activeTheme.keyBackgroundColor)
            }
            holder.textView.setPadding(0, 0, 0, 0)
            holder.textView.setTextSize(TypedValue.COMPLEX_UNIT_SP, if (data.length > 2) 14f else 20f)
            holder.tVSdb.visibility = View.GONE
        } else {
            holder.tVSdb.visibility = View.GONE
        }
'''
    text = text[:start] + new_block + text[end:]
    write(path, text)


if __name__ == '__main__':
    if not SDK.exists():
        raise SystemExit('yuyansdk submodule is missing')
    patch_symbol_container()
    patch_symbol_adapter()
