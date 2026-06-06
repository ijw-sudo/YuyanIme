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


def patch_base_keyboard_view() -> None:
    path = SDK / "src/main/java/com/yuyan/imemodule/keyboard/BaseKeyboardView.kt"
    text = read(path)
    if "fun onEnterLongPress()" in text:
        write(path, text)
        return
    old = "            val softKey = mCurrentKey!!\n            val keyboardSymbol = ThemeManager.prefs.keyboardSymbol.getValue()"
    new = "            val softKey = mCurrentKey!!\n            if (softKey.code == KeyEvent.KEYCODE_ENTER) {\n                mAbortKey = true\n                mLongPressKey = false\n                mService?.onEnterLongPress()\n                dismissPreview()\n                return\n            }\n            val keyboardSymbol = ThemeManager.prefs.keyboardSymbol.getValue()"
    write(path, replace_required(text, old, new, "enter long press hook"))


def patch_ime_service() -> None:
    path = SDK / "src/main/java/com/yuyan/imemodule/service/ImeService.kt"
    text = read(path)
    if "ExtractedTextRequest" not in text:
        text = replace_required(
            text,
            "import android.view.inputmethod.EditorInfo\n",
            "import android.view.inputmethod.EditorInfo\nimport android.view.inputmethod.ExtractedTextRequest\n",
            "extracted text import",
        )
    if "getTranslatableTextBeforeCursor" not in text:
        old = "    fun getTextBeforeCursor(length:Int) : String {\n        return currentInputConnection.getTextBeforeCursor(length, 0).toString()\n    }"
        new = "    fun getTextBeforeCursor(length:Int) : String {\n        return currentInputConnection.getTextBeforeCursor(length, 0).toString()\n    }\n\n    fun getTranslatableTextBeforeCursor(length: Int): String {\n        val inputConnection = currentInputConnection ?: return \"\"\n        val extracted = inputConnection.getExtractedText(ExtractedTextRequest(), 0)\n        val text = extracted?.text?.toString()\n        if (!text.isNullOrBlank()) {\n            val safeEnd = extracted.selectionEnd.coerceIn(0, text.length)\n            return text.substring(0, safeEnd).takeLast(length)\n        }\n        return inputConnection.getTextBeforeCursor(length, 0).toString()\n    }"
        text = replace_required(text, old, new, "translatable text helper")
    write(path, text)


def patch_input_view() -> None:
    path = SDK / "src/main/java/com/yuyan/imemodule/keyboard/InputView.kt"
    text = read(path)
    text, count = re.subn(
        r"val enterKeyToggleState: Int\s*get\(\) = when \{.*?\n\s*\}",
        "val enterKeyToggleState: Int\n        get() = when {\n            isAddPhrases -> 4\n            aiTranslationState == AITranslationState.TRANSLATING -> 11\n            else -> InputModeSwitcher.mToggleStates.imeAction\n        }",
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise SystemExit("failed to patch enterKeyToggleState")
    if "fun onEnterLongPress()" not in text:
        text = replace_required(
            text,
            "    override fun responseLongKeyEvent(result: Pair<PopupMenuMode, String>) {",
            "    fun onEnterLongPress() {\n        if (aiTranslationState == AITranslationState.TRANSLATING) return\n        DevicesUtils.tryVibrate(this)\n        triggerTranslation()\n    }\n\n    override fun responseLongKeyEvent(result: Pair<PopupMenuMode, String>) {",
            "onEnterLongPress method",
        )
    text = text.replace(
        "        val fullText = service.getTextBeforeCursor(5000)\n        val lastNewline = fullText.lastIndexOf('\\n')\n        val sourceText = if (lastNewline >= 0) fullText.substring(lastNewline + 1) else fullText",
        "        val sourceText = service.getTranslatableTextBeforeCursor(5000)",
        1,
    )
    text = text.replace("aiTranslationState = AITranslationState.TRANSLATED", "aiTranslationState = AITranslationState.IDLE")
    write(path, text)


if __name__ == "__main__":
    if not SDK.exists():
        raise SystemExit("yuyansdk submodule is missing")
    patch_base_keyboard_view()
    patch_ime_service()
    patch_input_view()
