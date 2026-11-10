package xin_xuan_glass_probe

import cui.*
import std.env.getCommandLine
import std.fs.Path
import xin_xuan_glass_probe.application.CatalogController
import xin_xuan_glass_probe.storage.{LocalStore, defaultDataRoot}

private func argument(name: String): ?String {
    let args = getCommandLine()
    for (i in 0..args.size - 1) { if (args[i] == name) { return Some(args[i + 1]) } }
    None
}

main(): Unit {
    diagnosticStage("G00_MAIN_ENTERED")
    configureShoppingFonts()
    diagnosticStage("G05_FONT_CONFIGURED")
    let assets = argument("--assets-dir").getOrDefault({=> Path(ApplicationPaths.basePath().getOrDefault({=> "."})).join(Path("assets")).toString()})
    // Explicit isolated data roots support verification without touching real user data.
    let root = argument("--test-data-dir").getOrDefault({=> defaultDataRoot()})
    let model = CatalogController(LocalStore(root), assets)
    let vm = CatalogViewModel(model)
    let materials = Backdrop(assetRoot: assets)
    diagnosticStage("G30_BEFORE_WINDOW")
    let app = DesktopApp(WindowSpec("心选购物", 760, 420), theme: shoppingTheme())
    diagnosticStage("G40_WINDOW_CREATED")
    app.manage(materials)
    app.setMinimumSize(640, 400)
    app.setCloseRequestHandler(Some({request => vm.requestClose(request)}))
    app.run { shoppingView(vm, materials) }
    println("NORMAL_EXIT")
}
