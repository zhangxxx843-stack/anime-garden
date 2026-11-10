package xin_xuan_glass_probe

import cui.*

func shoppingTheme(): Theme {
    Theme(bg: Color.rgb(230, 240, 239), panel: Color.rgba(247, 255, 252, 110),
        panelRaised: Color.rgba(247, 255, 252, 110), panelEdge: Color.rgba(255, 255, 255, 220),
        text: Color.rgb(28, 59, 63), mutedText: Color.rgb(75, 99, 99),
        accent: Color.rgb(32, 111, 93), accentText: Color.rgb(255, 255, 255), danger: Color.rgb(157, 68, 60),
        field: Color.rgba(252, 255, 254, 215), fieldActive: Color.rgba(255, 255, 255, 245))
}

@When[os == "Linux"]
func configureShoppingFonts(): Unit {
    // Host-side visual verification only. Windows keeps its already-tested UI font.
    Fonts.register("XinXuanHostCJK", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    Fonts.setDefault(Some("XinXuanHostCJK"))
}

@When[os != "Linux"]
func configureShoppingFonts(): Unit { Fonts.setDefault(FontRole.systemUI) }
