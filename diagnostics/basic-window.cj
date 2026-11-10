package xin_xuan_basic_window

import cui.*
import std.fs.File

main(): Unit {
    File.writeTo("basic-last-stage.txt", "B00_MAIN_ENTERED\n".toArray())
    let app = DesktopApp(WindowSpec("Xin Xuan - Basic Window Diagnostic", 640, 400))
    File.writeTo("basic-last-stage.txt", "B10_WINDOW_CREATED\n".toArray())
    app.run {
        File.writeTo("basic-last-stage.txt", "B20_UI_BUILDER_ENTERED\n".toArray())
        VStack {
            Label("Basic window / Chinese: 心选购物").fontSize(22.fp)
            Button("Test button", {=> println("BASIC_BUTTON_OK")})
        }.spacing(16.vp).padding(24.vp)
    }
    File.writeTo("basic-last-stage.txt", "B30_NORMAL_EXIT\n".toArray())
    println("BASIC_WINDOW_OK")
}
